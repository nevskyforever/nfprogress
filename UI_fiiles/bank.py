# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bankDyxjLn.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_Bamk(object):
    def setupUi(self, Bamk):
        if not Bamk.objectName():
            Bamk.setObjectName(u"Bamk")
        Bamk.resize(562, 303)
        font = QFont()
        font.setFamilies([u"Arial"])
        Bamk.setFont(font)
        self.gridLayout = QGridLayout(Bamk)
        self.gridLayout.setObjectName(u"gridLayout")
        self.deposit_total_sum = QLabel(Bamk)
        self.deposit_total_sum.setObjectName(u"deposit_total_sum")

        self.gridLayout.addWidget(self.deposit_total_sum, 1, 2, 1, 1)

        self.return_deposit_date = QLabel(Bamk)
        self.return_deposit_date.setObjectName(u"return_deposit_date")

        self.gridLayout.addWidget(self.return_deposit_date, 1, 3, 1, 1)

        self.credit_status = QLabel(Bamk)
        self.credit_status.setObjectName(u"credit_status")

        self.gridLayout.addWidget(self.credit_status, 1, 0, 1, 1)

        self.credit_total_sum = QLabel(Bamk)
        self.credit_total_sum.setObjectName(u"credit_total_sum")

        self.gridLayout.addWidget(self.credit_total_sum, 0, 2, 1, 1)

        self.widget = QWidget(Bamk)
        self.widget.setObjectName(u"widget")
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.widget_2 = QWidget(self.widget)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout = QHBoxLayout(self.widget_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.take_credit_btn = QPushButton(self.widget_2)
        self.take_credit_btn.setObjectName(u"take_credit_btn")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.take_credit_btn.sizePolicy().hasHeightForWidth())
        self.take_credit_btn.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.take_credit_btn)

        self.return_credit_btn = QPushButton(self.widget_2)
        self.return_credit_btn.setObjectName(u"return_credit_btn")
        sizePolicy.setHeightForWidth(self.return_credit_btn.sizePolicy().hasHeightForWidth())
        self.return_credit_btn.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.return_credit_btn)

        self.make_deposit_btn = QPushButton(self.widget_2)
        self.make_deposit_btn.setObjectName(u"make_deposit_btn")
        sizePolicy.setHeightForWidth(self.make_deposit_btn.sizePolicy().hasHeightForWidth())
        self.make_deposit_btn.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.make_deposit_btn)

        self.return_deposit_btn = QPushButton(self.widget_2)
        self.return_deposit_btn.setObjectName(u"return_deposit_btn")
        sizePolicy.setHeightForWidth(self.return_deposit_btn.sizePolicy().hasHeightForWidth())
        self.return_deposit_btn.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.return_deposit_btn)


        self.gridLayout_2.addWidget(self.widget_2, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.widget, 2, 0, 1, 4)

        self.return_credit_date = QLabel(Bamk)
        self.return_credit_date.setObjectName(u"return_credit_date")

        self.gridLayout.addWidget(self.return_credit_date, 0, 3, 1, 1)

        self.deposit_status = QLabel(Bamk)
        self.deposit_status.setObjectName(u"deposit_status")

        self.gridLayout.addWidget(self.deposit_status, 0, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 1, 1, 1)


        self.retranslateUi(Bamk)

        QMetaObject.connectSlotsByName(Bamk)
    # setupUi

    def retranslateUi(self, Bamk):
        Bamk.setWindowTitle(QCoreApplication.translate("Bamk", u"\u0411\u0430\u043d\u043a", None))
        self.deposit_total_sum.setText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u0441\u043d\u044f\u0442\u0438\u044e", None))
        self.return_deposit_date.setText(QCoreApplication.translate("Bamk", u"\u0414\u0430\u0442\u0430 \u0441\u043d\u044f\u0442\u0438\u044f", None))
        self.credit_status.setText(QCoreApplication.translate("Bamk", u"\u0412 \u0431\u0430\u043d\u043a\u0435 \u043d\u0435\u0442 \u043a\u0440\u0435\u0434\u0438\u0442\u0430", None))
        self.credit_total_sum.setText(QCoreApplication.translate("Bamk", u"\u0421\u0443\u043c\u043c\u0430 \u043a \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0443", None))
        self.take_credit_btn.setText(QCoreApplication.translate("Bamk", u"\u0412\u0437\u044f\u0442\u044c \u043a\u0440\u0435\u0434\u0438\u0442", None))
        self.return_credit_btn.setText(QCoreApplication.translate("Bamk", u"\u041f\u043e\u0433\u0430\u0441\u0438\u0442\u044c \u043a\u0440\u0435\u0434\u0438\u0442", None))
        self.make_deposit_btn.setText(QCoreApplication.translate("Bamk", u"\u0412\u043d\u0435\u0441\u0442\u0438 \u0432\u043a\u043b\u0430\u0434", None))
        self.return_deposit_btn.setText(QCoreApplication.translate("Bamk", u"\u0421\u043d\u044f\u0442\u044c\u0442 \u0432\u043a\u043b\u0430\u0434", None))
        self.return_credit_date.setText(QCoreApplication.translate("Bamk", u"\u0414\u0430\u0442\u0430 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0430", None))
        self.deposit_status.setText(QCoreApplication.translate("Bamk", u"\u0412 \u0431\u0430\u043d\u043a\u0435 \u043d\u0435\u0442 \u0432\u043a\u043b\u0430\u0434\u0430", None))
    # retranslateUi

