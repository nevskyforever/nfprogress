from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Property

class ToastNotification(QFrame):
    def __init__(self, parent, message, duration=3000, position="bottom-right"):
        super().__init__(parent)
        self.position = position
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Базовый стиль (менеджер переопределит под тип уведомления)
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
        layout.addWidget(self.label)

        # Эффект прозрачности для анимации
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self._opacity = 1.0

        # Анимация появления
        self.fade_in_anim = QPropertyAnimation(self, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.valueChanged.connect(self._update_opacity)

        # Анимация исчезновения
        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.valueChanged.connect(self._update_opacity)
        self.fade_out_anim.finished.connect(self.close)

        # Таймер для автоматического закрытия
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        self.timer.start(duration)

        self.adjustSize()  # сразу вычисляем размер

    # ---------- Методы для управления позицией (вызываются менеджером) ----------
    def set_global_position(self, x, y):
        """Устанавливает глобальные координаты уведомления (относительно родителя)."""
        self.move(x, y)

    # ---------- Свойства для анимации ----------
    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        self.opacity_effect.setOpacity(value)

    def _update_opacity(self, value):
        self.opacity_effect.setOpacity(value)

    def start_fade_out(self):
        """Запускает анимацию исчезновения (вызывается менеджером или таймером)."""
        self.fade_out_anim.start()

    opacity = Property(float, get_opacity, set_opacity)