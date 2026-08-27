# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lottery_ticket.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_lottery_ticket_dialog(object):
    def setupUi(self, lottery_ticket_dialog):
        if not lottery_ticket_dialog.objectName():
            lottery_ticket_dialog.setObjectName(u"lottery_ticket_dialog")
        lottery_ticket_dialog.resize(560, 360)
        self.main_layout = QVBoxLayout(lottery_ticket_dialog)
        self.main_layout.setObjectName(u"main_layout")
        self.title_label = QLabel(lottery_ticket_dialog)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.title_label)

        self.hint_label = QLabel(lottery_ticket_dialog)
        self.hint_label.setObjectName(u"hint_label")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.hint_label)

        self.numbers_layout = QGridLayout()
        self.numbers_layout.setObjectName(u"numbers_layout")
        self.player_caption = QLabel(lottery_ticket_dialog)
        self.player_caption.setObjectName(u"player_caption")

        self.numbers_layout.addWidget(self.player_caption, 0, 0, 1, 1)

        self.winning_caption = QLabel(lottery_ticket_dialog)
        self.winning_caption.setObjectName(u"winning_caption")

        self.numbers_layout.addWidget(self.winning_caption, 1, 0, 1, 1)


        self.main_layout.addLayout(self.numbers_layout)

        self.result_label = QLabel(lottery_ticket_dialog)
        self.result_label.setObjectName(u"result_label")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)

        self.main_layout.addWidget(self.result_label)

        self.close_button = QPushButton(lottery_ticket_dialog)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setEnabled(False)

        self.main_layout.addWidget(self.close_button)


        self.retranslateUi(lottery_ticket_dialog)

        QMetaObject.connectSlotsByName(lottery_ticket_dialog)
    # setupUi

    def retranslateUi(self, lottery_ticket_dialog):
        lottery_ticket_dialog.setWindowTitle(QCoreApplication.translate("lottery_ticket_dialog", u"\u041b\u043e\u0442\u0435\u0440\u0435\u0439\u043d\u044b\u0439 \u0431\u0438\u043b\u0435\u0442", None))
#if QT_CONFIG(accessibility)
        lottery_ticket_dialog.setAccessibleName(QCoreApplication.translate("lottery_ticket_dialog", u"\u0420\u043e\u0437\u044b\u0433\u0440\u044b\u0448 \u043b\u043e\u0442\u0435\u0440\u0435\u0439\u043d\u043e\u0433\u043e \u0431\u0438\u043b\u0435\u0442\u0430", None))
#endif // QT_CONFIG(accessibility)
        self.title_label.setText(QCoreApplication.translate("lottery_ticket_dialog", u"\U0001f39f\U0000fe0f \U00000420\U0000043e\U00000437\U0000044b\U00000433\U00000440\U0000044b\U00000448 \U000000ab5 \U00000438\U00000437 30\U000000bb", None))
        self.hint_label.setText(QCoreApplication.translate("lottery_ticket_dialog", u"\u0427\u0438\u0441\u043b\u0430 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u044e\u0442\u0441\u044f\u2026", None))
        self.player_caption.setText(QCoreApplication.translate("lottery_ticket_dialog", u"\u0412\u0430\u0448\u0438 \u0447\u0438\u0441\u043b\u0430", None))
        self.winning_caption.setText(QCoreApplication.translate("lottery_ticket_dialog", u"\u0412\u044b\u0438\u0433\u0440\u044b\u0448\u043d\u044b\u0435 \u0447\u0438\u0441\u043b\u0430", None))
        self.result_label.setText("")
        self.close_button.setText(QCoreApplication.translate("lottery_ticket_dialog", u"\u0417\u0430\u043a\u0440\u044b\u0442\u044c", None))
    # retranslateUi

