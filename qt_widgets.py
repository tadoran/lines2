from itertools import chain

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from game_logic import GameField
from resources import Sounds


class Percent:
    def __init__(self, base_val: int):
        self._base = base_val
        self.scaler = base_val * 0.01

    def __call__(self, percents):
        return percents * self.scaler


class QLabelNumber(QLabel):
    def __init__(self, *args, number: int = 0, **kwargs):
        super(QLabelNumber, self).__init__(*args, **kwargs)
        self.display(number)
        min_width = self.fontMetrics().boundingRect("00000").width()
        self.setMinimumWidth(min_width)
        # self.setMinimumHeight(50)

    def display(self, number: int):
        self.setText("Scores: " + str(number))


class NextColorItemWidget(QPushButton):
    def __init__(self, *args, **kwargs):
        super(NextColorItemWidget, self).__init__(*args, **kwargs)
        self.setFixedSize(30, 30)

        self.gradient = None
        self.pct = Percent(self.rect().width())

    def construct_gradient(self, color: QColor = QColor("magenta")):
        gr = QRadialGradient()
        gr.setCoordinateMode(QGradient.StretchToDeviceMode)
        c1 = color.lighter(150)
        c2 = color.darker(450)

        gr.setColorAt(0.05, c1)
        gr.setColorAt(0.49, color)
        gr.setColorAt(1.0, c2)
        gr.setCenter(QPointF(0.7, 0.3))

        gr.setFocalPoint(QPointF(0.7, 0.3))
        self.gradient = gr

    def changed(self):
        self.construct_gradient(color)
        self.update()

    def resizeEvent(self, e: QResizeEvent):
        super().resizeEvent(e)
        self.pct = Percent(self.rect().width())

    def paintEvent(self, e: QPaintEvent):
        # super().paintEvent(e)
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)

        pct = self.pct
        if self.gradient:
            rect = QRectF(self.rect()).marginsAdded(QMarginsF() - (pct(10)))
            shadow_rect = QRectF(rect)
            shadow_rect.translate(QPoint(pct(-1), pct(1)))
            shadow_rect.adjust(pct(-2), pct(2), pct(0), pct(2))

            shadow_color = QColor("#000000")
            shadow_color.setAlpha(100)

            painter.setBrush(shadow_color)
            painter.drawEllipse(shadow_rect)

            painter.setBrush(self.gradient)
            painter.drawEllipse(rect)

        painter.end()


class NextColorsWidget(QWidget):

    def __init__(self, logic_source: object, show_next: bool = True, *args, **kwargs):
        super(NextColorsWidget, self).__init__(*args, **kwargs)
        self.logic_source = logic_source
        self.show_next = show_next
        self.logic_source.show_next_signal.connect(self.show_next_colors)

        self.next_colors_len = logic_source.SPAWN_PER_TURN

        layout = QHBoxLayout()
        layout.setContentsMargins(QMargins())
        layout.setSpacing(0)

        label = QLabel("Next:")

        layout.addWidget(label)
        layout.addStretch()
        self.items = []
        for i in range(self.next_colors_len):
            nc_widget = NextColorItemWidget(self)
            layout.addWidget(nc_widget)
            self.items.append(nc_widget)

        layout.addStretch()

        # self.setMinimumHeight(50)
        self.setLayout(layout)

    def show_next_colors(self, show_next: bool):
        self.show_next = show_next
        self.setVisible(show_next)

    def update_next_colors(self, next_colors: list):
        items_available = len(next_colors)
        for i, item in enumerate(self.items):
            color = QColor(next_colors[i].color)
            if i <= items_available:
                item.construct_gradient(color)
            else:
                item.gradient = None
            item.update()

    # def paintEvent(self, e: QPaintEvent):
    #     painter = QPainter(self)
    #     painter.fillRect(self.rect(), QColor("blue"))
    #     super(NextColorsWidget, self).paintEvent(e)


class FieldItemWidget(QPushButton):
    changed = pyqtSignal(QObject)
    leftButtonPressed = pyqtSignal(QObject)
    rightButtonPressed = pyqtSignal(QObject)

    def __init__(self, y, x, *args, **kwargs):
        super(FieldItemWidget, self).__init__(*args, **kwargs)
        self._y = y
        self._x = x
        size_policy = QSizePolicy.Expanding
        policy = QSizePolicy()
        policy.setHorizontalPolicy(size_policy)
        policy.setVerticalPolicy(size_policy)
        policy.setWidthForHeight(True)
        self.setSizePolicy(policy)

        self.logic_source = self.parent().logic_source.items[x, y]
        self.logic_source.changed.connect(self.changed)

        self.logic_source.parent_field.show_next_signal.connect(self.show_next_colors)
        self.logic_source.active_status_changed.connect(self.toggle_active_state)

        self.show_next = self.logic_source.parent_field.show_next_colors
        self.logic_source.next_color.connect(self.set_next_color)
        self.next_color = None

        self.gradient = None
        self.construct_gradient()

        self.active = False
        self.active_timer = QTimer()
        self.active_timer.setInterval(300)
        self.active_timer.timeout.connect(self.toggle_active_state_animation)

        self.active_size_toggled = False
        self.self_size_modifier = 1

    def show_next_colors(self, show_next: bool):
        self.show_next = show_next
        self.update()

    def set_next_color(self, next_color):
        self.next_color = next_color
        if next_color:
            self.construct_gradient(next_color)
        self.update()

    def toggle_active_state(self, is_active):
        timer = self.active_timer
        self.active = is_active
        if is_active:
            timer.start()
            self.nativeParentWidget().sounds.tick2.play()
        else:
            self.self_size_modifier = 1
            timer.stop()
        self.update()

    def toggle_active_state_animation(self):
        self.active_size_toggled = not self.active_size_toggled
        if self.active_size_toggled and self.active_timer.isActive():
            self.self_size_modifier = 0.7
        else:
            self.self_size_modifier = 1
            self.nativeParentWidget().sounds.tick2.play()
        self.update()

    def construct_gradient(self, color: QColor = QColor("magenta")):
        gr = QRadialGradient()
        gr.setCoordinateMode(QGradient.StretchToDeviceMode)
        c1 = color.lighter(150)
        c2 = color.darker(450)

        gr.setColorAt(0.05, c1)
        gr.setColorAt(0.49, color)
        gr.setColorAt(1.0, c2)
        gr.setCenter(QPointF(0.7, 0.3))

        gr.setFocalPoint(QPointF(0.7, 0.3))
        self.gradient = gr

    def changed(self):
        if self.logic_source.item:
            self.construct_gradient(QColor(self.logic_source.item.color))
        elif self.next_color:
            self.construct_gradient(self.next_color)
        self.update()

    def resizeEvent(self, e: QResizeEvent):
        super().resizeEvent(e)
        self.pct = Percent(self.rect().width())

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)
        pct = self.pct
        painter.fillRect(self.rect().marginsAdded(QMargins() - 1), QColor("#d1d1d1"))
        # painter.fillRect(self.rect().marginsAdded(QMargins() - 1), QColor("#d24bcd"))

        if self.next_color and self.logic_source.item is None and self.show_next:
            rect = QRectF(self.rect()).marginsAdded((QMarginsF() - (pct(30))) / self.self_size_modifier)
            shadow_rect = QRectF(rect)
            shadow_rect.translate(QPoint(pct(-1), pct(1)))
            shadow_rect.adjust(pct(-2), pct(2), pct(0), pct(2))

            shadow_color = QColor("#000000")
            shadow_color.setAlpha(100)

            painter.setBrush(shadow_color)
            painter.drawEllipse(shadow_rect)

            painter.setBrush(self.gradient)
            painter.drawEllipse(rect)

        elif self.logic_source.item is not None:

            if self.active:
                active_color = QColor("white")
                active_color.setAlpha(120)
                brush = QBrush(active_color)
                painter.setBrush(brush)
                painter.drawRect(self.rect().marginsAdded(QMargins() - 2))

            rect = QRectF(self.rect()).marginsAdded((QMarginsF() - (pct(10))) / self.self_size_modifier)
            shadow_rect = QRectF(rect)
            shadow_rect.translate(QPoint(pct(-1), pct(1)))
            shadow_rect.adjust(pct(-2), pct(2), pct(0), pct(2))

            shadow_color = QColor("#000000")
            shadow_color.setAlpha(100)

            painter.setBrush(shadow_color)
            painter.drawEllipse(shadow_rect)

            painter.setBrush(self.gradient)
            painter.drawEllipse(rect)

        painter.end()

    def sizeHint(self):
        return QSize(50, 50)

    def minimumSizeHint(self):
        return QSize(self.sizeHint().width() // 2, self.sizeHint().height() // 2)

    def __repr__(self):
        return f"FieldItemWidget({self._y}, {self._x})"

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.leftButtonPressed.emit(self)
        elif e.button() == Qt.RightButton:
            self.rightButtonPressed.emit(self)
        else:
            pass


class GameFieldWidget(QWidget):
    def __init__(self, logic_source, *args, **kwargs):
        super(GameFieldWidget, self).__init__(*args, **kwargs)

        self.logic_source = logic_source

        self.logic_source.item_moved.connect(self.parent().sounds.tick2.play)
        self.logic_source.cells_cleared.connect(self.parent().sounds.line_cleared.play)

        layout = QGridLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        layout.heightForWidth(True)
        self.fieldItems2D = []
        height, width = logic_source.items._container.shape

        for y in range(height):
            self.fieldItems2D.append([])
            for x in range(width):
                item = FieldItemWidget(y, x, parent=self)
                self.fieldItems2D[y].append(item)
                layout.addWidget(item, y, x)
                item.leftButtonPressed.connect(self.item_clicked)
                item.rightButtonPressed.connect(self.item_clicked)

        self.fieldItems = list(chain.from_iterable(self.fieldItems2D))

        self.ratio = 1
        self.adjusted_to_size = (-1, -1)

    def resizeEvent(self, e:QResizeEvent):
        # https://stackoverflow.com/a/61589941/13537384
        size = e.size()
        if size == self.adjusted_to_size:
            # Avoid infinite recursion. I suspect Qt does this for you,
            # but it's best to be safe.
            return
        self.adjusted_to_size = size

        full_width = size.width()
        full_height = size.height()
        width = min(full_width, full_height * self.ratio)
        height = min(full_height, full_width / self.ratio)

        h_margin = round((full_width - width) / 2)
        v_margin = round((full_height - height) / 2)

        self.setContentsMargins(h_margin, v_margin, h_margin, v_margin)

    def item_clicked(self, item):
        self.logic_source.cell_clicked(item.logic_source)


class InformationBar(QWidget):
    def __init__(self, logic_source, *args, **kwargs):

        super(InformationBar, self).__init__(*args, **kwargs)

        self.logic_source = logic_source
        self.next_colors = NextColorsWidget(logic_source, parent=self)
        self.scores_counter = QLabelNumber(self)

        font = QFont("Segoe Script", 13)
        self.setFont(font)
        palette = self.palette()
        palette.setColor(self.foregroundRole(), QColor("white"))
        self.setPalette(palette)

        layout = QHBoxLayout()
        self.setLayout(layout)
        self.setFixedHeight(50)
        layout.addWidget(self.next_colors, alignment=Qt.AlignLeft)
        layout.addWidget(self.scores_counter, alignment=Qt.AlignRight)

        self.logic_source.next_colors_generated.connect(self.next_colors.update_next_colors)
        self.parent().current_scores.connect(self.update_counter)

    def reset(self):
        self.scores_counter.display(0)

    def update_counter(self, value):
        self.scores_counter.display(value)


class GameActions(QObject):
    def __init__(self, *args, **kwargs):
        super(GameActions, self).__init__(*args, **kwargs)
        # self.spawnAction = QAction("Spawn", self)
        # self.spawnAction.triggered.connect(self.parent().logic_source.spawn_items)
        self.resetAction = QAction("Reset", self)
        self.resetAction.triggered.connect(self.parent().logic_source.reset)

        self.toggleSound = QAction("Sound", self)
        self.toggleSound.triggered.connect(self.parent().sounds.toggle_sound)
        self.toggleSound.setCheckable(True)
        self.toggleSound.setChecked(True)

        self.show_next_colors = QAction("Next colors", self)
        self.show_next_colors.setCheckable(True)
        self.show_next_colors.setChecked(self.parent().logic_source.show_next_colors)
        self.show_next_colors.triggered.connect(self.parent().logic_source.toggle_show_next_colors)


class GameMenu(QMenuBar):
    def __init__(self, *args, **kwargs):
        super(GameMenu, self).__init__(*args, **kwargs)

        file_menu = self.addMenu("File")
        # file_menu.addAction(self.parent().game_actions.spawnAction)
        file_menu.addAction(self.parent().game_actions.resetAction)
        file_menu.addAction(self.parent().game_actions.show_next_colors)
        file_menu.addAction(self.parent().game_actions.toggleSound)


class MainWindow(QMainWindow):
    current_scores = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Lines")
        self.setWindowIcon(QIcon("FILE.ico"))
        self.sounds = Sounds()
        # self.menuBar().show()

        self.logic_source = GameField(10, 10)

        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        layout = QVBoxLayout()
        self.mainWidget.setLayout(layout)

        self.status_bar = InformationBar(logic_source=self.logic_source, parent=self)
        layout.addWidget(self.status_bar)

        layout.addWidget(GameFieldWidget(logic_source=self.logic_source, parent=self))

        self.scores = 0

        self.game_actions = GameActions(self)

        self.menu = GameMenu(self)
        self.setMenuBar(self.menu)

        self.logic_source.cells_cleared.connect(self.add_scores)
        self.logic_source.field_was_reset.connect(self.reset_scores)

        size_policy = QSizePolicy.Minimum
        policy = QSizePolicy()
        policy.setHorizontalPolicy(size_policy)
        policy.setVerticalPolicy(size_policy)
        # policy.setWidthForHeight(True)
        self.setSizePolicy(policy)
        self.logic_source.spawn_items()
        self.show()

    def reset_scores(self):
        self.scores = 0
        self.current_scores.emit(self.scores)
        self.sounds.restart.play()

    def add_scores(self, cells_cleared):
        self.scores += cells_cleared * cells_cleared
        self.current_scores.emit(self.scores)

    def paintEvent(self, e: QPaintEvent) -> None:
        super(MainWindow, self).paintEvent(e)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("black"))
        painter.end()
