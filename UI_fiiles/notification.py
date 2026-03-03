from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, \
    QGraphicsOpacityEffect  # QGraphicsOpacityEffect из QtWidgets, а не QtGui!
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Property
from PySide6.QtGui import QColor  # QColor все еще из QtGui


class ToastNotification(QFrame):
    def __init__(self, parent, message, duration=3000, position="bottom-right"):
        super().__init__(parent)

        # Настройка внешнего вида
        self.position = position

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Временно делаем ярким для отладки
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 0, 0, 220);
                border: 2px solid black;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        # Создание содержимого
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
        self.fade_in_anim.valueChanged.connect(self.update_opacity)

        # Анимация исчезновения
        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.valueChanged.connect(self.update_opacity)
        self.fade_out_anim.finished.connect(self.close)

        # Таймер для автоматического закрытия
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        self.timer.start(duration)

        # Позиционирование
        self.adjustSize()

        # Важно: перемещаем после установки размера
        QTimer.singleShot(0, self.move_to_position)

        # Показываем и запускаем анимацию
        self.show()
        self.raise_()
        self.fade_in_anim.start()

    def move_to_position(self):
        """Размещение в указанной позиции относительно родителя"""

        parent_rect = self.parent().rect()

        margin = 20

        if self.position == "top-right":
            x = parent_rect.width() - self.width() - margin
            y = margin
        elif self.position == "top-left":
            x = margin
            y = margin
        elif self.position == "bottom-left":
            x = margin
            y = parent_rect.height() - self.height() - margin
        elif self.position == "top-center":
            x = (parent_rect.width() - self.width()) // 2
            y = margin
        elif self.position == "bottom-center":
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - margin
        else:  # bottom-right (по умолчанию)
            x = parent_rect.width() - self.width() - margin
            y = parent_rect.height() - self.height() - margin

        self.move(x, y)

    def showEvent(self, event):
        """Переопределяем showEvent для гарантии правильной позиции при показе"""
        super().showEvent(event)
        self.move_to_position()
        self.raise_()
        self.activateWindow()

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        self.opacity_effect.setOpacity(value)

    def update_opacity(self, value):
        self.opacity_effect.setOpacity(value)

    def start_fade_out(self):
        self.fade_out_anim.start()

    opacity = Property(float, get_opacity, set_opacity)