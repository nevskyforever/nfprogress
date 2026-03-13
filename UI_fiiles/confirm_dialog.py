# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'confirm_dialogcFNxNM.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)

class Ui_confirm_dialog(object):
    def setupUi(self, confirm_dialog):
        if not confirm_dialog.objectName():
            confirm_dialog.setObjectName(u"confirm_dialog")
        confirm_dialog.resize(350, 150)
        confirm_dialog.setMinimumSize(QSize(223, 98))
        font = QFont()
        font.setFamilies([u"Arial"])
        confirm_dialog.setFont(font)
        self.verticalLayout = QVBoxLayout(confirm_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.message = QLabel(confirm_dialog)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.verticalLayout.addWidget(self.message)

        self.b = QDialogButtonBox(confirm_dialog)
        self.b.setObjectName(u"b")
        self.b.setOrientation(Qt.Orientation.Horizontal)
        self.b.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.b.setCenterButtons(True)

        self.verticalLayout.addWidget(self.b)


        self.retranslateUi(confirm_dialog)
        self.b.accepted.connect(confirm_dialog.accept)
        self.b.rejected.connect(confirm_dialog.reject)

        QMetaObject.connectSlotsByName(confirm_dialog)
    # setupUi

    def retranslateUi(self, confirm_dialog):
        confirm_dialog.setWindowTitle(QCoreApplication.translate("confirm_dialog", u"\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435", None))
        self.message.setText(QCoreApplication.translate("confirm_dialog", u"\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435", None))
    # retranslateUi

