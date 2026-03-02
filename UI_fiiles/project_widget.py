# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'project_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QProgressBar,
    QSizePolicy, QVBoxLayout, QWidget)

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
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Project Widget", None))
        self.deadline.setText(QCoreApplication.translate("Form", u"Дедлайн", None))
        self.streak_status.setText(QCoreApplication.translate("Form", u"Статус стрика", None))
        self.name.setText(QCoreApplication.translate("Form", u"Название", None))
        self.symbols.setText(QCoreApplication.translate("Form", u"Символы", None))
        self.streak.setText(QCoreApplication.translate("Form", u"Стрик", None))
    # retranslateUi