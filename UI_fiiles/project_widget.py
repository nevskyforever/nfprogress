from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt, QRectF, QEasingCurve, QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QPainter,
                           QPen)
from PySide6.QtWidgets import (QGridLayout, QLabel, QProgressBar,
                               QSizePolicy, QVBoxLayout, QWidget)
from PySide6.scripts.pyside_tool import project
from engine import streak_length as get_streak_length


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
        self._start_color = QColor(169, 169, 169)  # светло-серый
        self._end_color = QColor(76, 175, 80)  # зелёный

        # Анимация
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(500)  # мс
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._on_animation_value_changed)
        self._animation.finished.connect(self._on_animation_finished)

        self._initializing = True
        self._target_value = 0  # Целевое значение для анимации

    def _on_animation_value_changed(self, value):
        """Обновляет значение во время анимации"""
        self._value = value
        self.update()

    def _on_animation_finished(self):
        """Убеждаемся, что конечное значение точно установлено"""
        self._value = self._target_value
        self.update()

    def setValue(self, value, animated=True):
        """Устанавливает значение прогресса (0-100) с поддержкой анимации в обе стороны"""
        value = max(0, min(100, value))

        # Если значение не изменилось, ничего не делаем
        if abs(value - self._value) < 0.001 and not self._animation.state():
            return

        if self._initializing:
            animated = False
            self._initializing = False

        self._target_value = value

        if not animated:
            # Без анимации - просто устанавливаем значение
            self._animation.stop()
            self._value = value
            self.update()
            return

        # С анимацией - запускаем анимацию от текущего к целевому значению
        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(value)
        self._animation.start()

    def stopAnimation(self):
        """Останавливает текущую анимацию"""
        self._animation.stop()

    def setValueImmediate(self, value):
        """Устанавливает значение мгновенно без анимации"""
        value = max(0, min(100, value))
        self._animation.stop()
        self._value = value
        self._target_value = value
        self.update()

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

        # ВАЖНО: Устанавливаем фиксированный размер ДО добавления в сетку
        self.circular_progress.setFixedSize(90, 90)

        # Устанавливаем цвета градиента
        self.circular_progress.setStartColor("#A9A9A9")  # светло-серый для 0%
        self.circular_progress.setEndColor("#4CAF50")  # зелёный для 100%
        self.circular_progress.setBackgroundColor("#E0E0E0")

        # Убираем Expanding политику, так как размер фиксированный
        self.circular_progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 4. Заменяем старый прогресс-бар в сетке
        self.gridLayout.addWidget(self.circular_progress, 1, 0, 1, 1)

        # 5. Центрируем в ячейке
        self.gridLayout.setAlignment(self.circular_progress, Qt.AlignCenter)
        for row in (0, 2, 3, 4, 5):
            self.gridLayout.setRowStretch(row, 1)
        self.gridLayout.setRowStretch(1, 0)
        # Гарантируем минимальную высоту строки с прогресс-баром,
        # чтобы лейблы не перекрывали его на Windows (разные DPI/шрифты)
        self.gridLayout.setRowMinimumHeight(1, 95)

        # Увеличиваем вертикальный промежуток между строками, чтобы текст не касался круга
        self.gridLayout.setVerticalSpacing(15)

        # Добавляем отступы от краёв виджета для лучшего визуального восприятия
        self.gridLayout.setContentsMargins(10, 10, 10, 10)

        # 6. Обеспечиваем, что внутренний виджет-контейнер расширяется
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Настройка текстовых меток ---
        for label in (self.name, self.symbols, self.deadline,
                      self.streak, self.streak_status):
            label.setWordWrap(True)  # разрешаем перенос строк
            # Preferred вместо MinimumExpanding: лейблы не разрастаются
            # бесконтрольно на Windows с крупными системными шрифтами
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.project = project
        # raise_() вместо lower(): прогресс-бар поверх Z-стека,
        # иначе на Windows лейблы рисуются поверх кольца
        self.circular_progress.raise_()

        # Словарь для отображения единиц измерения
        self.unit_display = {
            'symbols': 'симв.',
            'A4': 'л.',
            'author_list': 'а.л.',
            'ficbook_pages': 'стр.'
        }

        self.update_display()

    def stop_animations(self):
        """Останавливает все анимации виджета перед его удалением.

        Без этого QVariantAnimation продолжает тикать после того, как
        QListWidget.clear() уничтожает виджет, и PySide пытается вызвать
        слот на уже удалённом C++ объекте ("Called attribute on invalid object").
        """
        self.circular_progress.stopAnimation()

    def update_display(self):
        """Обновляет отображение виджета проекта."""
        self.name.setText(self.project.name)

        # Прогресс (всегда в процентах)
        if self.project.goal != float('inf'):
            self.circular_progress.setValue(int(self.project.progress), animated=True)
        else:
            self.circular_progress.setValue(100, animated=False)

        # Значения уже в единице проекта с отображением единицы измерения
        total_str = self._format_number(self.project.total_units)
        if self.project.goal != float('inf'):
            goal_str = self._format_number(self.project.goal)
        else:
            goal_str = '∞'

        # Получаем сокращённое название единицы измерения
        unit_short = self.unit_display.get(self.project.unit, '')

        # Формируем строку с единицей измерения: "10/20 стр." или "5/10 л." и т.д.
        self.symbols.setText(f'{total_str}/{goal_str} {unit_short}')

        # Сначала скрываем все элементы стриков
        self.streak.setVisible(False)
        self.streak_status.setVisible(False)

        # Дедлайн
        if self.project.deadline_str != 'Нет':
            self.deadline.setText(f'Дедлайн: {self.project.deadline_str}')
            self.deadline.setVisible(True)

            # Показываем стрики только если они включены в настройках
            if self.global_streak_mode:
                streak_status = self.project.get_streak_status()
                streak_length = get_streak_length(self.project.streaks)
                self.streak.setText(f'Стрик: {streak_length} д.')
                self.streak.setVisible(True)

                status_msg = self.project.get_streak_status_msg('min')
                self.streak_status.setText(status_msg)
                self.streak_status.setVisible(True)
        else:
            self.deadline.setVisible(False)

        # Обновляем геометрию
        self.updateGeometry()
        self.widget.updateGeometry()

    def _format_number(self, num):
        """Форматирует число для отображения."""
        if isinstance(num, float):
            if num.is_integer() or abs(num - round(num)) < 0.0001:
                return str(int(round(num)))
            # Оставляем 1-2 знака после запятой, убираем лишние нули
            return f"{num:.2f}".rstrip('0').rstrip('.') if '.' in f"{num:.2f}" else str(int(num))
        return str(num)
