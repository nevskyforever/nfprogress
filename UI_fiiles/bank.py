# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bankVajTLn.ui'
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
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QWidget)

class Ui_Bamk(object):
    def setupUi(self, Bamk):
        if not Bamk.objectName():
            Bamk.setObjectName(u"Bamk")
        Bamk.resize(396, 427)
        Bamk.setMinimumSize(QSize(381, 392))
        font = QFont()
        font.setFamilies([u"Arial"])
        Bamk.setFont(font)
        self.gridLayout = QGridLayout(Bamk)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widget = QWidget(Bamk)
        self.widget.setObjectName(u"widget")
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.make_a_loan_payment = QPushButton(self.widget)
        self.make_a_loan_payment.setObjectName(u"make_a_loan_payment")

        self.gridLayout_2.addWidget(self.make_a_loan_payment, 3, 0, 1, 1)

        self.loan_partial_repayment_amount = QLineEdit(self.widget)
        self.loan_partial_repayment_amount.setObjectName(u"loan_partial_repayment_amount")

        self.gridLayout_2.addWidget(self.loan_partial_repayment_amount, 4, 0, 1, 1)

        self.make_deposit_btn = QPushButton(self.widget)
        self.make_deposit_btn.setObjectName(u"make_deposit_btn")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.make_deposit_btn.sizePolicy().hasHeightForWidth())
        self.make_deposit_btn.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.make_deposit_btn, 2, 1, 1, 1)

        self.take_credit_btn = QPushButton(self.widget)
        self.take_credit_btn.setObjectName(u"take_credit_btn")
        sizePolicy.setHeightForWidth(self.take_credit_btn.sizePolicy().hasHeightForWidth())
        self.take_credit_btn.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.take_credit_btn, 2, 0, 1, 1)

        self.active_deposit_topup_amount = QLineEdit(self.widget)
        self.active_deposit_topup_amount.setObjectName(u"active_deposit_topup_amount")

        self.gridLayout_2.addWidget(self.active_deposit_topup_amount, 4, 1, 1, 1)

        self.return_credit_btn = QPushButton(self.widget)
        self.return_credit_btn.setObjectName(u"return_credit_btn")
        sizePolicy.setHeightForWidth(self.return_credit_btn.sizePolicy().hasHeightForWidth())
        self.return_credit_btn.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.return_credit_btn, 7, 0, 1, 1)

        self.partial_loan_repayment = QPushButton(self.widget)
        self.partial_loan_repayment.setObjectName(u"partial_loan_repayment")
        self.partial_loan_repayment.setFlat(False)

        self.gridLayout_2.addWidget(self.partial_loan_repayment, 5, 0, 1, 1)

        self.return_deposit_btn = QPushButton(self.widget)
        self.return_deposit_btn.setObjectName(u"return_deposit_btn")
        sizePolicy.setHeightForWidth(self.return_deposit_btn.sizePolicy().hasHeightForWidth())
        self.return_deposit_btn.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.return_deposit_btn, 3, 1, 1, 1)

        self.withdraw_interest_from_a_deposit = QPushButton(self.widget)
        self.withdraw_interest_from_a_deposit.setObjectName(u"withdraw_interest_from_a_deposit")
        sizePolicy.setHeightForWidth(self.withdraw_interest_from_a_deposit.sizePolicy().hasHeightForWidth())
        self.withdraw_interest_from_a_deposit.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.withdraw_interest_from_a_deposit, 5, 1, 1, 1)

        self.scrollArea = QScrollArea(self.widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 346, 208))
        self.gridLayout_3 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.deposit_status = QLabel(self.scrollAreaWidgetContents)
        self.deposit_status.setObjectName(u"deposit_status")
        self.deposit_status.setWordWrap(True)

        self.gridLayout_3.addWidget(self.deposit_status, 0, 0, 1, 1)

        self.deposit_total_sum = QLabel(self.scrollAreaWidgetContents)
        self.deposit_total_sum.setObjectName(u"deposit_total_sum")
        self.deposit_total_sum.setWordWrap(True)

        self.gridLayout_3.addWidget(self.deposit_total_sum, 0, 1, 1, 1)

        self.return_deposit_date = QLabel(self.scrollAreaWidgetContents)
        self.return_deposit_date.setObjectName(u"return_deposit_date")

        self.gridLayout_3.addWidget(self.return_deposit_date, 0, 2, 1, 1)

        self.credit_status = QLabel(self.scrollAreaWidgetContents)
        self.credit_status.setObjectName(u"credit_status")
        self.credit_status.setWordWrap(True)

        self.gridLayout_3.addWidget(self.credit_status, 1, 0, 1, 1)

        self.credit_total_sum = QLabel(self.scrollAreaWidgetContents)
        self.credit_total_sum.setObjectName(u"credit_total_sum")
        self.credit_total_sum.setWordWrap(True)

        self.gridLayout_3.addWidget(self.credit_total_sum, 1, 1, 1, 1)

        self.return_credit_date = QLabel(self.scrollAreaWidgetContents)
        self.return_credit_date.setObjectName(u"return_credit_date")

        self.gridLayout_3.addWidget(self.return_credit_date, 1, 2, 1, 1)

        self.credit_score = QLabel(self.scrollAreaWidgetContents)
        self.credit_score.setObjectName(u"credit_score")

        self.gridLayout_3.addWidget(self.credit_score, 2, 0, 1, 1)

        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout_3.addWidget(self.label_2, 2, 1, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        self.label.setWordWrap(True)

        self.gridLayout_3.addWidget(self.label, 2, 2, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 2)


        self.gridLayout.addWidget(self.widget, 2, 0, 1, 2)


        self.retranslateUi(Bamk)

        QMetaObject.connectSlotsByName(Bamk)
    # setupUi

    def retranslateUi(self, Bamk):
        Bamk.setWindowTitle(QCoreApplication.translate("Bamk", u"\u0411\u0430\u043d\u043a", None))
        self.make_a_loan_payment.setText(QCoreApplication.translate("Bamk", u"\u0412\u043d\u0435\u0441\u0442\u0438 \u043f\u043b\u0430\u0442\u0435\u0436", None))
        self.loan_partial_repayment_amount.setPlaceholderText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u043f\u043e\u0433\u0430\u0448\u0435\u043d\u0438\u044e (100.0)", None))
        self.make_deposit_btn.setText(QCoreApplication.translate("Bamk", u"\u0412\u043d\u0435\u0441\u0442\u0438 \u0432\u043a\u043b\u0430\u0434", None))
        self.take_credit_btn.setText(QCoreApplication.translate("Bamk", u"\u0412\u0437\u044f\u0442\u044c \u043a\u0440\u0435\u0434\u0438\u0442", None))
        self.active_deposit_topup_amount.setPlaceholderText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044e (100.0)", None))
        self.return_credit_btn.setText(QCoreApplication.translate("Bamk", u"\u041f\u043e\u0433\u0430\u0441\u0438\u0442\u044c \u043a\u0440\u0435\u0434\u0438\u0442", None))
        self.partial_loan_repayment.setText(QCoreApplication.translate("Bamk", u"\u0427\u0430\u0441\u0442\u0438\u0447\u043d\u043e\u0435 \u043f\u043e\u0433\u0430\u0448\u0435\u043d\u0438\u0435", None))
        self.return_deposit_btn.setText(QCoreApplication.translate("Bamk", u"\u0421\u043d\u044f\u0442\u044c \u0432\u043a\u043b\u0430\u0434", None))
        self.withdraw_interest_from_a_deposit.setText(QCoreApplication.translate("Bamk", u"\u0421\u043d\u044f\u0442\u044c \u043f\u0440\u043e\u0446\u0435\u043d\u0442\u044b", None))
        self.deposit_status.setText(QCoreApplication.translate("Bamk", u"\u0412 \u0431\u0430\u043d\u043a\u0435 \u043d\u0435\u0442 \u0432\u043a\u043b\u0430\u0434\u0430", None))
        self.deposit_total_sum.setText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u0441\u043d\u044f\u0442\u0438\u044e", None))
        self.return_deposit_date.setText(QCoreApplication.translate("Bamk", u"\u0414\u0430\u0442\u0430 \u0441\u043d\u044f\u0442\u0438\u044f", None))
        self.credit_status.setText(QCoreApplication.translate("Bamk", u"\u0412 \u0431\u0430\u043d\u043a\u0435 \u043d\u0435\u0442 \u043a\u0440\u0435\u0434\u0438\u0442\u0430", None))
        self.credit_total_sum.setText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0443", None))
        self.return_credit_date.setText(QCoreApplication.translate("Bamk", u"\u0414\u0430\u0442\u0430 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0430", None))
        self.credit_score.setText(QCoreApplication.translate("Bamk", u"\u041a\u0440\u0435\u0434\u0438\u0442\u043d\u044b\u0439 \u0440\u0435\u0439\u0442\u0438\u043d\u0433", None))
        self.label_2.setText(QCoreApplication.translate("Bamk", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0435 \u043f\u0440\u043e\u0446\u0435\u043d\u0442\u044b", None))
        self.label.setText(QCoreApplication.translate("Bamk", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0434\u043e\u0445\u043e\u0434", None))
    # retranslateUi

