from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt, QRectF, QEasingCurve, QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QPainter,
                           QPen)
from PySide6.QtWidgets import (QGridLayout, QLabel, QProgressBar,
                               QSizePolicy, QVBoxLayout, QWidget)
from engine import load_settings as settings


# =============================================================================
# Кастомный виджет кругового прогресс-бара
# =============================================================================
class CircularProgressBar(QWidget):
    """Круговой прогресс-бар в виде кольца"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._text_visible = False
        self._ring_width = 8
        self._background_color = QColor(220, 220, 220)
        self._progress_color = QColor(76, 175, 80)  # оставляем для обратной совместимости
        self._text_color = QColor(0, 0, 0)
        # Важно: минимальные размеры должны быть равны, чтобы круг не сплющивался
        self.setMinimumSize(80, 80)

        # Цвета для градиента прогресса
        self._start_color = QColor(255, 0, 0)  # красный
        self._end_color = QColor(76, 175, 80)  # зелёный

        # Анимация
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(500)  # мс
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._on_animation_value_changed)

        self._initializing = True

    def _on_animation_value_changed(self, value):
        self._value = value
        self.update()

    def setValue(self, value, animated=True):
        """Устанавливает значение прогресса (0-100)"""
        value = max(0, min(100, value))

        if self._initializing:
            animated = False
            self._initializing = False

        if not animated:
            self._value = value
            self.update()
            return

        if abs(value - self._value) < 0.001:
            return

        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(value)
        self._animation.start()

    def value(self):
        return self._value

    def setTextVisible(self, visible):
        self._text_visible = visible
        self.update()

    def setRingWidth(self, width):
        """Устанавливает толщину кольца в пикселях"""
        self._ring_width = width
        self.update()

    def setBackgroundColor(self, color):
        """Устанавливает цвет фонового кольца"""
        self._background_color = QColor(color)
        self.update()

    def setProgressColor(self, color):
        """Устанавливает фиксированный цвет кольца прогресса"""
        self._progress_color = QColor(color)
        # Обновляем конечный цвет градиента
        self._end_color = QColor(color)
        self.update()

    def setStartColor(self, color):
        """Устанавливает начальный цвет градиента (для 0%)"""
        self._start_color = QColor(color)
        self.update()

    def setEndColor(self, color):
        """Устанавливает конечный цвет градиента (для 100%)"""
        self._end_color = QColor(color)
        self.update()

    def _get_color_for_progress(self, progress):
        """Возвращает цвет на основе прогресса с плавной интерполяцией в цветовом пространстве"""
        ratio = max(0.0, min(1.0, progress / 100.0))

        # Вариант 2: Интерполяция в HSV (более плавная и естественная)
        start_hsv = self._start_color.toHsv()
        end_hsv = self._end_color.toHsv()

        h = start_hsv.hue() + ratio * (end_hsv.hue() - start_hsv.hue())
        s = start_hsv.saturation() + ratio * (end_hsv.saturation() - start_hsv.saturation())
        v = start_hsv.value() + ratio * (end_hsv.value() - start_hsv.value())

        # Нормализуем значения
        h = h % 360  # оттенок по кругу
        s = max(0, min(255, s))
        v = max(0, min(255, v))

        color = QColor()
        color.setHsv(int(h), int(s), int(v))
        return color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Рассчитываем квадратную область для рисования кольца
        margin = self._ring_width / 2
        side = min(self.width(), self.height()) - 2 * margin
        if side <= 0:
            return

        # Центрируем квадрат
        x = (self.width() - side) / 2
        y = (self.height() - side) / 2
        rect = QRectF(x, y, side, side)  # используем QRectF для точности

        # Перо
        pen = QPen()
        pen.setWidth(self._ring_width)
        pen.setCapStyle(Qt.RoundCap)

        # Фоновое кольцо
        pen.setColor(self._background_color)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Кольцо прогресса с динамическим цветом
        current_color = self._get_color_for_progress(self._value)
        pen.setColor(current_color)
        painter.setPen(pen)
        start_angle = 90 * 16
        span_angle = -self._value * 360 * 16 / 100
        painter.drawArc(rect, start_angle, int(span_angle))

        # Текст (опционально)
        if self._text_visible:
            painter.setPen(self._text_color)
            font = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, f"{self._value:.0f}%")


# =============================================================================
# Исходный UI-класс (сгенерирован Qt Designer)
# =============================================================================
class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(185, 181)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(Form)
        self.widget.setObjectName(u"widget")
        self.widget.setEnabled(True)
        self.widget.setBaseSize(QSize(0, 0))
        font = QFont()
        font.setFamilies([u"Arial"])
        self.widget.setFont(font)
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")

        # Стандартный QProgressBar (будет заменён)
        self.progressBar = QProgressBar(self.widget)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(24)
        self.gridLayout.addWidget(self.progressBar, 1, 0, 1, 1)

        self.deadline = QLabel(self.widget)
        self.deadline.setObjectName(u"deadline")
        self.deadline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gridLayout.addWidget(self.deadline, 3, 0, 1, 1)

        self.streak_status = QLabel(self.widget)
        self.streak_status.setObjectName(u"streak_status")
        self.streak_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gridLayout.addWidget(self.streak_status, 5, 0, 1, 1)

        self.name = QLabel(self.widget)
        self.name.setObjectName(u"name")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gridLayout.addWidget(self.name, 0, 0, 1, 1)

        self.symbols = QLabel(self.widget)
        self.symbols.setObjectName(u"symbols")
        self.symbols.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gridLayout.addWidget(self.symbols, 2, 0, 1, 1)

        self.streak = QLabel(self.widget)
        self.streak.setObjectName(u"streak")
        self.streak.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gridLayout.addWidget(self.streak, 4, 0, 1, 1)

        self.verticalLayout.addWidget(self.widget)

        self.retranslateUi(Form)
        QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Project Widget", None))
        self.deadline.setText(QCoreApplication.translate("Form", u"Дедлайн", None))
        self.streak_status.setText(QCoreApplication.translate("Form", u"Статус стрика", None))
        self.name.setText(QCoreApplication.translate("Form", u"Название", None))
        self.symbols.setText(QCoreApplication.translate("Form", u"Символы", None))
        self.streak.setText(QCoreApplication.translate("Form", u"Стрик", None))


# =============================================================================
# Финальный класс виджета проекта (используется в main_UI.py)
# =============================================================================
class ProjectWidget(QWidget, Ui_Form):
    def __init__(self, project, global_streak_mode):
        super().__init__()
        self.setupUi(self)
        # Загружаем настройки
        self.global_streak_mode = global_streak_mode
        # 1. Сбрасываем фиксированный размер, установленный в .ui
        self.resize(0, 0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        # 2. Удаляем стандартный QProgressBar
        self.progressBar.deleteLater()

        # 3. Создаём круговой прогресс-бар
        self.circular_progress = CircularProgressBar(self.widget)
        self.circular_progress.setTextVisible(False)
        self.circular_progress.setRingWidth(12)

        # Устанавливаем цвета градиента
        self.circular_progress.setStartColor("#FF0000")  # красный для 0%
        self.circular_progress.setEndColor("#4CAF50")  # зелёный для 100%

        self.circular_progress.setBackgroundColor("#E0E0E0")
        self.circular_progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 4. Заменяем старый прогресс-бар в сетке
        self.gridLayout.addWidget(self.circular_progress, 1, 0, 1, 1)

        # 5. Настраиваем растяжение строк сетки:
        self.gridLayout.setRowStretch(1, 1)  # круговой прогресс-бар
        for row in (0, 2, 3, 4, 5):
            self.gridLayout.setRowStretch(row, 0)

        # 6. Обеспечиваем, что внутренний виджет-контейнер расширяется
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- ДОБАВЛЕНО: настройка текстовых меток ---
        for label in (self.name, self.symbols, self.deadline,
                      self.streak, self.streak_status):
            label.setWordWrap(True)  # разрешаем перенос строк
            label.setSizePolicy(QSizePolicy.Preferred,  # по горизонтали как обычно
                                QSizePolicy.MinimumExpanding)  # по вертикали может расти

        self.project = project
        self.circular_progress.lower()
        self.update_display()

    def update_display(self):
        self.name.setText(self.project.name)
        self.circular_progress.setValue(int(self.project.progress), animated=True)
        self.symbols.setText(f'{self.project.total_symbols}/{self.project.goal}')

        # Управление видимостью стриков в зависимости от режима
        if not self.global_streak_mode:
            self.streak.setVisible(False)
            self.streak_status.setVisible(False)

        if self.project.deadline_str != 'Нет':
            self.deadline.setText(f'Дедлайн: {self.project.deadline_str}')
            self.deadline.setVisible(True)

            if self.global_streak_mode:
                self.streak.setText(f'Стрик: {len(self.project.streaks)} д.')
                self.streak.setVisible(True)
                self.streak_status.setText(self.project.get_streak_status_msg('min'))
                self.streak_status.setVisible(True)
        else:
            self.deadline.setVisible(False)

        self.updateGeometry()
        self.widget.updateGeometry()