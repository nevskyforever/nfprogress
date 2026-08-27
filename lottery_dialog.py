"""Анимированное окно раскрытия результата лотерейного билета."""
from random import randint

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QDialog, QLabel

from UI_fiiles.lottery_ticket import Ui_lottery_ticket_dialog
from localization import tr


class LotteryTicketDialog(QDialog, Ui_lottery_ticket_dialog):
    """Показывает пять пар чисел и выделяет совпадения после остановки барабанов."""

    TICKS_PER_NUMBER = 6

    def __init__(self, draw, parent=None):
        super().__init__(parent)
        self.draw = draw
        self._tick_count = 0
        self._revealed_count = 0
        self._player_labels = []
        self._winning_labels = []
        self.setupUi(self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._apply_translation()
        self._create_number_labels()
        self.close_button.clicked.connect(self.accept)

        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._animate_numbers)
        self._timer.start()

    def _apply_translation(self):
        self.setWindowTitle(tr('Лотерейный билет'))
        self.setAccessibleName(tr('Розыгрыш лотерейного билета'))
        self.title_label.setText(tr('🎟️ Розыгрыш «5 из 30»'))
        self.hint_label.setText(tr('Числа определяются…'))
        self.player_caption.setText(tr('Ваши числа'))
        self.winning_caption.setText(tr('Выигрышные числа'))
        self.close_button.setText(tr('Закрыть'))

    def _create_number_labels(self):
        for row, target in ((0, self._player_labels), (1, self._winning_labels)):
            for column in range(5):
                label = QLabel('—', self)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setMinimumSize(54, 54)
                label.setStyleSheet(self._number_style('#3c4656'))
                font = QFont(label.font())
                font.setPointSize(16)
                font.setBold(True)
                label.setFont(font)
                self.numbers_layout.addWidget(label, row, column + 1)
                target.append(label)

    @staticmethod
    def _number_style(color):
        return (
            'QLabel { background: ' + color + '; color: white; border-radius: 27px; '
            'padding: 8px; margin: 3px; }'
        )

    def _animate_numbers(self):
        for labels in (self._player_labels, self._winning_labels):
            for index in range(self._revealed_count, len(labels)):
                labels[index].setText(str(randint(1, 30)))

        self._tick_count += 1
        if self._tick_count % self.TICKS_PER_NUMBER:
            return

        index = self._revealed_count
        player_number = self.draw['player_numbers'][index]
        winning_number = self.draw['winning_numbers'][index]
        player_is_match = player_number in self.draw['winning_numbers']
        winning_is_match = winning_number in self.draw['player_numbers']
        self._player_labels[index].setText(str(player_number))
        self._winning_labels[index].setText(str(winning_number))
        self._player_labels[index].setStyleSheet(
            self._number_style('#2e9d59' if player_is_match else '#b34a4a')
        )
        self._winning_labels[index].setStyleSheet(
            self._number_style('#2e9d59' if winning_is_match else '#b34a4a')
        )
        self._revealed_count += 1

        if self._revealed_count == 5:
            self._timer.stop()
            self._show_result()

    def _show_result(self):
        matches = self.draw['matches']
        prize = self.draw['prize']
        if prize:
            self.result_label.setText(
                tr(f'Совпало чисел: {matches}. Выигрыш: {prize} монет!')
            )
        else:
            self.result_label.setText(tr(f'Совпало чисел: {matches}. В этот раз не повезло :('))
        self.hint_label.setText(tr('Зелёным отмечены совпадения, красным — несовпадения.'))
        self.close_button.setEnabled(True)
