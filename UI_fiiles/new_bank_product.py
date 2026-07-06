# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'new_bank_productBhasPA.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDateEdit, QDialog,
    QDialogButtonBox, QGridLayout, QLabel, QLineEdit,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(234, 269)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.scrollArea = QScrollArea(Dialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 208, 203))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.product_description = QLabel(self.scrollAreaWidgetContents)
        self.product_description.setObjectName(u"product_description")

        self.verticalLayout.addWidget(self.product_description)

        self.lineEdit = QLineEdit(self.scrollAreaWidgetContents)
        self.lineEdit.setObjectName(u"lineEdit")

        self.verticalLayout.addWidget(self.lineEdit)

        self.return_date_label = QLabel(self.scrollAreaWidgetContents)
        self.return_date_label.setObjectName(u"return_date_label")

        self.verticalLayout.addWidget(self.return_date_label)

        self.return_date_dateedit = QDateEdit(self.scrollAreaWidgetContents)
        self.return_date_dateedit.setObjectName(u"return_date_dateedit")
        self.return_date_dateedit.setCalendarPopup(True)

        self.verticalLayout.addWidget(self.return_date_dateedit)

        self.product_interest_rates = QLabel(self.scrollAreaWidgetContents)
        self.product_interest_rates.setObjectName(u"product_interest_rates")
        self.product_interest_rates.setWordWrap(True)

        self.verticalLayout.addWidget(self.product_interest_rates)

        self.total_amount_to_be_refunded = QLabel(self.scrollAreaWidgetContents)
        self.total_amount_to_be_refunded.setObjectName(u"total_amount_to_be_refunded")
        self.total_amount_to_be_refunded.setWordWrap(True)

        self.verticalLayout.addWidget(self.total_amount_to_be_refunded)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"\u041d\u043e\u0432\u044b\u0439 \u043f\u0440\u043e\u0434\u0443\u043a\u0442", None))
        self.product_description.setText(QCoreApplication.translate("Dialog", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("Dialog", u"\u0421\u0443\u043c\u043c\u0430 (100.0)", None))
        self.return_date_label.setText(QCoreApplication.translate("Dialog", u"\u0414\u0430\u0442\u0430 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0430:", None))
        self.product_interest_rates.setText(QCoreApplication.translate("Dialog", u"\u041f\u0440\u043e\u0446\u0435\u043d\u0442\u044b", None))
        self.total_amount_to_be_refunded.setText(QCoreApplication.translate("Dialog", u"\u0418\u0442\u043e\u0433\u043e\u0432\u0430\u044f \u0441\u0443\u043c\u043c\u0430 \u043a \u0432\u043e\u0432\u0437\u0440\u0430\u0442\u0443", None))
    # retranslateUi

