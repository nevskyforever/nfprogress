# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gamer_editcImtNb.ui'
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
    QGridLayout, QLabel, QLineEdit, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_gamer_editor(object):
    def setupUi(self, gamer_editor):
        if not gamer_editor.objectName():
            gamer_editor.setObjectName(u"gamer_editor")
        gamer_editor.resize(400, 300)
        font = QFont()
        font.setFamilies([u"Arial"])
        gamer_editor.setFont(font)
        self.gridLayout = QGridLayout(gamer_editor)
        self.gridLayout.setObjectName(u"gridLayout")
        self.level = QLineEdit(gamer_editor)
        self.level.setObjectName(u"level")

        self.gridLayout.addWidget(self.level, 1, 2, 1, 1)

        self.label_3 = QLabel(gamer_editor)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 4, 1, 1, 1)

        self.label_2 = QLabel(gamer_editor)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 3, 1, 1, 1)

        self.exp = QLineEdit(gamer_editor)
        self.exp.setObjectName(u"exp")

        self.gridLayout.addWidget(self.exp, 4, 2, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 3, 3, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 3, 0, 1, 1)

        self.label = QLabel(gamer_editor)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 1, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 5, 1, 1, 1)

        self.label_4 = QLabel(gamer_editor)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 2, 1, 1, 1)

        self.coins = QLineEdit(gamer_editor)
        self.coins.setObjectName(u"coins")

        self.gridLayout.addWidget(self.coins, 3, 2, 1, 1)

        self.health = QLineEdit(gamer_editor)
        self.health.setObjectName(u"health")

        self.gridLayout.addWidget(self.health, 2, 2, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_2, 0, 1, 1, 1)

        self.buttonBox = QDialogButtonBox(gamer_editor)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 6, 3, 1, 1)


        self.retranslateUi(gamer_editor)
        self.buttonBox.accepted.connect(gamer_editor.accept)
        self.buttonBox.rejected.connect(gamer_editor.reject)

        QMetaObject.connectSlotsByName(gamer_editor)
    # setupUi

    def retranslateUi(self, gamer_editor):
        gamer_editor.setWindowTitle(QCoreApplication.translate("gamer_editor", u"\u0420\u0435\u0434\u0430\u043a\u0442\u043e\u0440 \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430", None))
        self.label_3.setText(QCoreApplication.translate("gamer_editor", u"\u041e\u043f\u044b\u0442:", None))
        self.label_2.setText(QCoreApplication.translate("gamer_editor", u"\u041c\u043e\u043d\u0435\u0442\u044b:", None))
        self.label.setText(QCoreApplication.translate("gamer_editor", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c:", None))
        self.label_4.setText(QCoreApplication.translate("gamer_editor", u"\u0417\u0434\u043e\u0440\u043e\u0432\u044c\u0435:", None))
    # retranslateUi

