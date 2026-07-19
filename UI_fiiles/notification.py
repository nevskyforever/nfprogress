from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Property
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QGraphicsOpacityEffect, QSizePolicy


class ToastNotification(QFrame):
    def __init__(self, parent, message, duration=3000, position="bottom-right", manager=None):
        super().__init__(parent)
        self.manager = manager                     # сохраняем ссылку на менеджер
        self.position = position
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        parent_width = parent.width() if parent else 560
        max_label_width = max(140, min(520, parent_width - 60))
        metrics = QFontMetrics(self.label.font())
        natural_width = max((metrics.horizontalAdvance(line) for line in message.splitlines()), default=0)
        label_width = min(max_label_width, max(140, natural_width + 4))
        self.setMaximumWidth(label_width + 40)
        self.label.setFixedWidth(label_width)
        self.label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.label)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self._opacity = 1.0

        self.fade_in_anim = QPropertyAnimation(self, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.valueChanged.connect(self._update_opacity)

        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.valueChanged.connect(self._update_opacity)
        self.fade_out_anim.finished.connect(self.close)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        self.timer.start(duration)

        self.adjustSize()

    def set_global_position(self, x, y):
        self.move(x, y)

    def mousePressEvent(self, event):
        self.start_fade_out()
        super().mousePressEvent(event)

    def start_fade_out(self):
        """Запуск исчезновения. Сначала уведомляем менеджера, потом анимацию."""
        if self.manager:
            self.manager.remove_toast_before_fade(self)   # убираем из списка для пересчёта
        self.fade_out_anim.start()

    # ---------- Свойства для анимации ----------
    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        self.opacity_effect.setOpacity(value)

    def _update_opacity(self, value):
        self.opacity_effect.setOpacity(value)

    opacity = Property(float, get_opacity, set_opacity)
