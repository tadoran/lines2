from copy import deepcopy
from random import sample, choice

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QPoint, QRect
from PyQt5.QtGui import QColor
from enums import CoordinatesMoves
from tableContainer import NpTableContainer


class GameItem(QObject):
    ''' Ball with color and status '''

    def __init__(self, color, cell=None):
        super(GameItem, self).__init__()
        self.color = color
        self.cell = cell

    @property
    def cell(self):
        return self._cell

    @cell.setter
    def cell(self, cell):
        self._cell = cell
        if cell is None and self._cell:
            del self.item
            return
        if cell:
            if cell.item != self:
                cell.item = self

    @cell.deleter
    def cell(self):
        self._cell.item = None
        self._cell = None

    def __str__(self):
        in_cell = "" if not self.cell else f" in cell {self.cell}"
        return f"{str(self.color).capitalize()} point{in_cell}"

    def __repr__(self):
        return f"GameItem('{self.color}', {self.cell})"


class GameCell(QObject):
    """Contains blueprint of a cell on game field"""
    changed = pyqtSignal()
    active_status_changed = pyqtSignal(bool)
    next_color = pyqtSignal(object)

    def __init__(self, parent_field, x: int, y: int, item: GameItem = None):
        super(GameCell, self).__init__()
        self.parent_field = parent_field
        parent_field.field_was_reset.connect(self.reset)
        self.x = x
        self.y = y
        self.item = item
        self.changed.emit()
        self._active = False

    @property
    def item(self):
        return self._item

    @item.setter
    def item(self, item):
        self._item = item
        if item is None and self._item:
            del self.item
            return

        if item and item.cell != self._item:
            item.cell = self
        self.changed.emit()

    @item.deleter
    def item(self):
        del self._item.cell
        self._item = None

        self.changed.emit()

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, is_active: bool):
        self._active = is_active
        self.active_status_changed.emit(is_active)

    def is_in_full_line(self):
        pass

    def reset(self):
        self.item = None
        self.active = False
        self.next_color.emit(None)
        self.changed.emit()

    def __str__(self):
        return f"GameCell({self.y},{self.x})"

    def __repr__(self):
        return f"GameCell({self.y},{self.x})"


class GameField(QObject):
    """Contains game field and all logic of it"""
    WIDTH = 10
    HEIGHT = 10
    COLORS_ON_FIELD = 5
    SPAWN_PER_TURN = 5
    ITEMS_IN_LINE = 5
    MOVE_SPEED_MS = 50
    SHOW_NEXT_COLORS = True

    COLORS = ["blueviolet", "brown", "coral", "darkgreen", "darkmagenta", "darkorange", "deeppink", "gold",
              "limegreen", "mediumslateblue", "orangered", "white"]

    field_was_reset = pyqtSignal()
    cells_cleared = pyqtSignal(int)
    item_moved = pyqtSignal()
    loose = pyqtSignal()
    next_colors_generated = pyqtSignal(list)
    show_next_signal = pyqtSignal(bool)

    def __init__(self, width: int = 0, height: int = 0):
        super(GameField, self).__init__()

        self.field_colors = sample(self.COLORS, self.COLORS_ON_FIELD)
        if width != 0:
            self.WIDTH = width
        if height != 0:
            self.HEIGHT = height

        self.next_items = []
        self.next_items_positions = []
        self.show_next_colors = self.SHOW_NEXT_COLORS

        self.items = NpTableContainer(self.HEIGHT, self.WIDTH)
        self.active_item = None
        self.create_field_cells()

        self.create_game_items(self.SPAWN_PER_TURN)

        self.move_timer = QTimer()

        self.loose.connect(self.reset)

    def toggle_show_next_colors(self):
        self.show_next_colors = not self.show_next_colors
        self.show_next_signal.emit(self.show_next_colors)

    def create_field_cells(self):
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.items[y, x] = GameCell(self, y, x)

    def create_game_items(self, n: int = 0):
        if n == 0:
            n = self.SPAWN_PER_TURN

        for _ in range(n):
            item = GameItem(choice(self.field_colors))
            self.next_items.append(item)

        self.next_colors_generated.emit(self.next_items)

    def find_filled_cells(self):
        cells = np.ravel(self.items)
        empty_cells = [c for c in cells if c.item is not None]
        return empty_cells

    def find_empty_cells(self):
        cells = np.ravel(self.items)
        empty_cells = [c for c in cells if c.item is None]
        return empty_cells

    def create_next_items(self, n: int = 0):
        if n == 0:
            n = self.SPAWN_PER_TURN

        if len(self.next_items) < n:
            self.create_game_items(n - len(self.next_items))
        try:
            cells = sample(self.find_empty_cells(), n)
        except ValueError:
            self.loose.emit()
            return

        for c in cells:
            next_color = self.next_items.pop(0)
            self.next_items_positions.append((c, next_color))
            c.next_color.emit(QColor(next_color.color))

    def spawn_items(self, n: int = 0):
        if n == 0:
            n = self.SPAWN_PER_TURN

        if len(self.next_items_positions) < n:
            self.create_next_items(n - len(self.next_items_positions))

        for _ in range(n):
            cell, item = self.next_items_positions.pop(0)
            cell.next_color.emit(None)
            if cell.item is not None:
                cell = choice(self.find_empty_cells())

            cell.item = item
            line = self.cell_is_in_line(cell)
            if line:
                self.clear_line(line)
        self.create_next_items()

    def move_item(self, path: list, step: int = 0):

        current_cell_point = path[step]
        current_cell = self.items[current_cell_point.x(), current_cell_point.y()]

        if step < len(path) - 1:
            next_cell_point = path[step + 1]
            next_cell = self.items[next_cell_point.x(), next_cell_point.y()]

            next_cell.item = current_cell.item
            current_cell.item = None
            self.item_moved.emit()
            self.move_timer.singleShot(self.MOVE_SPEED_MS,
                                       lambda self=self, path=path, step=step: self.move_item(path, step + 1))

        else:
            target_cell_point = path[-1]
            cell = self.items[target_cell_point.x(), target_cell_point.y()]

            self.active_item.active = False
            self.active_item.item = None
            self.active_item = None

            line = self.cell_is_in_line(cell)
            if line:
                self.clear_line(line)
            else:
                self.spawn_items()

    def clear_line(self, line):
        for cell in line:
            cell.reset()
            cell.next_color.emit(None)
        self.cells_cleared.emit(len(line))
        # self.cells_cleared.emit()

    def reset(self):
        self.next_items = []
        self.next_items_positions = []
        self.active_item = None
        self.field_was_reset.emit()

        self.spawn_items()

    def find_path(self, start: GameCell, end: GameCell):
        field_map = self.items._container

        moves = CoordinatesMoves
        possible_moves = [moves.RIGHT, moves.DOWN, moves.LEFT, moves.UP]
        directions = [QPoint(*m.value) for m in possible_moves]
        field_rect = QRect(0, 0, self.WIDTH, self.HEIGHT)

        start_point = QPoint(start.x, start.y)
        if end:
            end_point = QPoint(end.x, end.y)
        else:
            end_point = QPoint()

        paths = [[start_point]]
        last_paths = paths
        visited_points = set()
        path_found = False
        found_path = []

        while not path_found and len(last_paths) > 0:
            paths.sort(key=lambda x, end=end_point: (x[-1] - end).manhattanLength(), reverse=True)
            last_paths = []
            for path in paths:
                last_point = path[-1]
                for d in directions:
                    next_point = last_point + d
                    if (field_rect.contains(next_point) and
                            not field_map[next_point.x(), next_point.y()].item and
                            not str(next_point) in visited_points
                    ):

                        visited_points.add(str(next_point))
                        new_path = deepcopy(path + [next_point])
                        last_paths.append(new_path)
                        if next_point == end_point:
                            return new_path
            else:
                paths = last_paths
                pass

            if len(last_paths) == 0 and not path_found:
                break
        return found_path

    def cell_is_in_line(self, cell):
        moves = CoordinatesMoves
        horizontal_moves = [moves.LEFT, moves.RIGHT]
        vertical_moves = [moves.UP, moves.DOWN]
        diagonal1_moves = [moves.UP_LEFT, moves.DOWN_RIGHT]
        diagonal2_moves = [moves.UP_RIGHT, moves.DOWN_LEFT]

        directions = [horizontal_moves, vertical_moves, diagonal1_moves, diagonal2_moves]

        field_items = self.items
        pw, ph = self.WIDTH, self.HEIGHT
        y, x = cell.y, cell.x
        for direction in directions:
            line_elements_count = 1
            line_elements = [cell]
            for move in direction:
                next_y, next_x = y, x
                while True:
                    next_y, next_x = next_y + move.value[0], next_x + move.value[1]
                    if 0 <= next_y < ph and 0 <= next_x < pw:
                        next_cell = field_items[next_x, next_y]
                        next_item = next_cell.item
                        if not next_item:
                            break

                        if cell.item is not None:
                            if next_item.color == cell.item.color:
                                line_elements_count += 1
                                line_elements += [next_cell]
                                continue
                            else:
                                break
                        else:
                            break
                    else:
                        break

            if line_elements_count >= self.ITEMS_IN_LINE:
                return line_elements
        return False

    def cell_clicked(self, cell):
        if not cell.active and cell.item:
            if self.active_item:
                self.active_item.active = False
                self.active_item = None
            cell.active = True
            self.active_item = cell

        if self.active_item and not cell.item:
            path = self.find_path(self.active_item, cell)
            if len(path) > 0:
                self.move_item(path)
