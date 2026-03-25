# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'freeze_projectLehcMj.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, Qt)
from PySide6.QtGui import (QFont)
from PySide6.QtWidgets import (QDialogButtonBox,
                               QLabel, QListWidget, QVBoxLayout)

class Ui_freeze_projrct(object):
    def setupUi(self, freeze_projrct):
        if not freeze_projrct.objectName():
            freeze_projrct.setObjectName(u"freeze_projrct")
        freeze_projrct.resize(400, 300)
        font = QFont()
        font.setFamilies([u"Arial"])
        freeze_projrct.setFont(font)
        self.verticalLayout = QVBoxLayout(freeze_projrct)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(freeze_projrct)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.list_projects = QListWidget(freeze_projrct)
        self.list_projects.setObjectName(u"list_projects")

        self.verticalLayout.addWidget(self.list_projects)

        self.label_2 = QLabel(freeze_projrct)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.verticalLayout.addWidget(self.label_2)

        self.buttonBox = QDialogButtonBox(freeze_projrct)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(freeze_projrct)
        self.buttonBox.accepted.connect(freeze_projrct.accept)
        self.buttonBox.rejected.connect(freeze_projrct.reject)

        QMetaObject.connectSlotsByName(freeze_projrct)
    # setupUi

    def retranslateUi(self, freeze_projrct):
        freeze_projrct.setWindowTitle(QCoreApplication.translate("freeze_projrct", u"\u0417\u0430\u043c\u043e\u0440\u043e\u0437\u043a\u0430 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
        self.label.setText(QCoreApplication.translate("freeze_projrct", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442 \u0434\u043b\u044f \u0437\u0430\u043c\u043e\u0440\u043e\u0437\u043a\u0438", None))
        self.label_2.setText(QCoreApplication.translate("freeze_projrct", u"\u0417\u0430\u043c\u043e\u0440\u043e\u0437\u0438\u0442\u044c \u043c\u043e\u0436\u043d\u043e \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u043e\u0435\u043a\u0442 \u0441 \u0438\u043c\u0435\u044e\u0449\u0438\u043c\u0441\u044f \u0441\u0442\u0440\u0438\u043a\u043e\u043c, \u0435\u0441\u043b\u0438 \u043e\u043d \u043d\u0435 \u043f\u0440\u043e\u0434\u043b\u0435\u043d.", None))
    # retranslateUi

