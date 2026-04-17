# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'create_projectWBRmnt.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDateEdit, QDialog, QDialogButtonBox, QGridLayout,
    QLabel, QLineEdit, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_create_project(object):
    def setupUi(self, create_project):
        if not create_project.objectName():
            create_project.setObjectName(u"create_project")
        create_project.resize(350, 320)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(create_project.sizePolicy().hasHeightForWidth())
        create_project.setSizePolicy(sizePolicy)
        create_project.setMinimumSize(QSize(350, 320))
        create_project.setMaximumSize(QSize(350, 320))
        font = QFont()
        font.setFamilies([u"Arial"])
        create_project.setFont(font)
        self.verticalLayout = QVBoxLayout(create_project)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.widget = QWidget(create_project)
        self.widget.setObjectName(u"widget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy1)
        self.widget.setMinimumSize(QSize(311, 200))
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_4 = QLabel(self.widget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setTextFormat(Qt.TextFormat.AutoText)
        self.label_4.setScaledContents(False)
        self.label_4.setOpenExternalLinks(False)

        self.gridLayout.addWidget(self.label_4, 4, 0, 1, 1)

        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.checkBox = QCheckBox(self.widget)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setCheckable(True)
        self.checkBox.setChecked(True)
        self.checkBox.setTristate(False)

        self.gridLayout.addWidget(self.checkBox, 2, 2, 1, 1)

        self.le_total_symbols = QLineEdit(self.widget)
        self.le_total_symbols.setObjectName(u"le_total_symbols")
        self.le_total_symbols.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.le_total_symbols, 4, 1, 1, 1)

        self.label_7 = QLabel(self.widget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setWordWrap(True)

        self.gridLayout.addWidget(self.label_7, 5, 0, 1, 1)

        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_5 = QLabel(self.widget)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 4, 2, 1, 1)

        self.label_6 = QLabel(self.widget)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout.addWidget(self.label_6, 1, 2, 1, 1)

        self.incorrect_data = QLabel(self.widget)
        self.incorrect_data.setObjectName(u"incorrect_data")
        self.incorrect_data.setEnabled(True)
        self.incorrect_data.setStyleSheet(u"QLabel {\n"
"    color: rgb(255, 0, 0);\n"
"}")
        self.incorrect_data.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.incorrect_data, 6, 0, 1, 3)

        self.cb_unit = QComboBox(self.widget)
        self.cb_unit.addItem("")
        self.cb_unit.addItem("")
        self.cb_unit.addItem("")
        self.cb_unit.addItem("")
        self.cb_unit.setObjectName(u"cb_unit")
        self.cb_unit.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.cb_unit, 5, 1, 1, 2)

        self.le_goal = QLineEdit(self.widget)
        self.le_goal.setObjectName(u"le_goal")
        self.le_goal.setText(u"1000")
        self.le_goal.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.le_goal, 1, 1, 1, 1)

        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.de_deadline = QDateEdit(self.widget)
        self.de_deadline.setObjectName(u"de_deadline")
        self.de_deadline.setEnabled(True)
        self.de_deadline.setDateTime(QDateTime(QDate(2026, 3, 1), QTime(16, 0, 0)))
        self.de_deadline.setMaximumDate(QDate(9999, 12, 31))
        self.de_deadline.setCalendarPopup(True)
        self.de_deadline.setDate(QDate(2026, 3, 1))

        self.gridLayout.addWidget(self.de_deadline, 2, 1, 1, 1)

        self.le_name = QLineEdit(self.widget)
        self.le_name.setObjectName(u"le_name")
        self.le_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.le_name, 0, 1, 1, 1)

        self.label_8 = QLabel(self.widget)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout.addWidget(self.label_8, 3, 0, 1, 1)

        self.le_personal_goal_for_the_day = QLineEdit(self.widget)
        self.le_personal_goal_for_the_day.setObjectName(u"le_personal_goal_for_the_day")
        self.le_personal_goal_for_the_day.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.le_personal_goal_for_the_day, 3, 1, 1, 1)

        self.label_9 = QLabel(self.widget)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 3, 2, 1, 1)


        self.verticalLayout.addWidget(self.widget)

        self.buttons = QDialogButtonBox(create_project)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setOrientation(Qt.Orientation.Horizontal)
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.buttons.setCenterButtons(True)

        self.verticalLayout.addWidget(self.buttons)


        self.retranslateUi(create_project)
        self.buttons.accepted.connect(create_project.accept)
        self.buttons.rejected.connect(create_project.reject)

        QMetaObject.connectSlotsByName(create_project)
    # setupUi

    def retranslateUi(self, create_project):
        create_project.setWindowTitle(QCoreApplication.translate("create_project", u"\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
        self.label_4.setText(QCoreApplication.translate("create_project", u"<html><head/><body><p>\u0422\u0435\u043a\u0443\u0449\u0435\u0435<br/>\u043a\u043e\u043b-\u0432\u043e</p></body></html>", None))
        self.label_2.setText(QCoreApplication.translate("create_project", u"\u0426\u0435\u043b\u044c", None))
        self.checkBox.setText(QCoreApplication.translate("create_project", u"\u041d\u0435\u0442", None))
        self.le_total_symbols.setText(QCoreApplication.translate("create_project", u"0", None))
        self.label_7.setText(QCoreApplication.translate("create_project", u"\u0427\u0442\u043e \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0435\u043c:", None))
        self.label.setText(QCoreApplication.translate("create_project", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_5.setText(QCoreApplication.translate("create_project", u"\u0435\u0434\u0438\u043d\u0438\u0446 (\u0447\u0438\u0441\u043b\u043e)", None))
        self.label_6.setText(QCoreApplication.translate("create_project", u"\u0435\u0434\u0438\u043d\u0438\u0446 (\u0447\u0438\u0441\u043b\u043e)", None))
        self.incorrect_data.setText(QCoreApplication.translate("create_project", u"<html><head/><body><p align=\"center\">\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435</p></body></html>", None))
        self.cb_unit.setItemText(0, QCoreApplication.translate("create_project", u"\u0421\u0438\u043c\u0432\u043e\u043b\u044b", None))
        self.cb_unit.setItemText(1, QCoreApplication.translate("create_project", u"\u041b\u0438\u0441\u0442\u044b \u04104", None))
        self.cb_unit.setItemText(2, QCoreApplication.translate("create_project", u"\u0410\u0432\u0442\u043e\u0440\u0441\u043a\u0438\u0435 \u043b\u0438\u0441\u0442\u044b", None))
        self.cb_unit.setItemText(3, QCoreApplication.translate("create_project", u"\u0421\u0442\u0440\u0430\u043d\u0438\u0446\u044b \u0424\u0438\u043a\u0431\u0443\u043a\u0430", None))

        self.label_3.setText(QCoreApplication.translate("create_project", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d", None))
        self.le_name.setText(QCoreApplication.translate("create_project", u"\u041d\u043e\u0432\u044b\u0439 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_8.setText(QCoreApplication.translate("create_project", u"\u0426\u0435\u043b\u044c \u043d\u0430 \u0434\u0435\u043d\u044c", None))
        self.le_personal_goal_for_the_day.setText(QCoreApplication.translate("create_project", u"0", None))
        self.label_9.setText(QCoreApplication.translate("create_project", u"\u0435\u0434\u0438\u043d\u0438\u0446 (\u0447\u0438\u0441\u043b\u043e)", None))
    # retranslateUi

