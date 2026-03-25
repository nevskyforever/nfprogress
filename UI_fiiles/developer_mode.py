# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gamer_editLXiTAv.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, Qt)
from PySide6.QtGui import (QFont)
from PySide6.QtWidgets import (QCheckBox, QDateEdit,
                               QDialogButtonBox, QGridLayout, QLabel,
                               QLineEdit, QSizePolicy, QSpacerItem)

class Ui_developer_node(object):
    def setupUi(self, developer_node):
        if not developer_node.objectName():
            developer_node.setObjectName(u"developer_node")
        developer_node.resize(400, 300)
        font = QFont()
        font.setFamilies([u"Arial"])
        developer_node.setFont(font)
        self.gridLayout = QGridLayout(developer_node)
        self.gridLayout.setObjectName(u"gridLayout")
        self.exp = QLineEdit(developer_node)
        self.exp.setObjectName(u"exp")

        self.gridLayout.addWidget(self.exp, 7, 2, 1, 1)

        self.health = QLineEdit(developer_node)
        self.health.setObjectName(u"health")

        self.gridLayout.addWidget(self.health, 5, 2, 1, 1)

        self.label = QLabel(developer_node)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 4, 1, 1, 1)

        self.test_date = QDateEdit(developer_node)
        self.test_date.setObjectName(u"test_date")

        self.gridLayout.addWidget(self.test_date, 1, 2, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 10, 2, 1, 1)

        self.label_3 = QLabel(developer_node)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 7, 1, 1, 1)

        self.label_4 = QLabel(developer_node)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 5, 1, 1, 1)

        self.buttonBox = QDialogButtonBox(developer_node)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 11, 3, 1, 1)

        self.coins = QLineEdit(developer_node)
        self.coins.setObjectName(u"coins")

        self.gridLayout.addWidget(self.coins, 6, 2, 1, 1)

        self.label_2 = QLabel(developer_node)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 6, 1, 1, 1)

        self.label_5 = QLabel(developer_node)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 3, 2, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 6, 3, 1, 1)

        self.level = QLineEdit(developer_node)
        self.level.setObjectName(u"level")

        self.gridLayout.addWidget(self.level, 4, 2, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 6, 0, 1, 1)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_3, 2, 2, 1, 1)

        self.test_date_cb = QCheckBox(developer_node)
        self.test_date_cb.setObjectName(u"test_date_cb")

        self.gridLayout.addWidget(self.test_date_cb, 1, 1, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_2, 0, 2, 1, 1)


        self.retranslateUi(developer_node)
        self.buttonBox.accepted.connect(developer_node.accept)
        self.buttonBox.rejected.connect(developer_node.reject)

        QMetaObject.connectSlotsByName(developer_node)
    # setupUi

    def retranslateUi(self, developer_node):
        developer_node.setWindowTitle(QCoreApplication.translate("developer_node", u"\u0420\u0435\u0436\u0438\u043c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u0447\u0438\u043a\u0430", None))
        self.label.setText(QCoreApplication.translate("developer_node", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c:", None))
        self.label_3.setText(QCoreApplication.translate("developer_node", u"\u041e\u043f\u044b\u0442:", None))
        self.label_4.setText(QCoreApplication.translate("developer_node", u"\u0417\u0434\u043e\u0440\u043e\u0432\u044c\u0435:", None))
        self.label_2.setText(QCoreApplication.translate("developer_node", u"\u041c\u043e\u043d\u0435\u0442\u044b:", None))
        self.label_5.setText(QCoreApplication.translate("developer_node", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.test_date_cb.setText(QCoreApplication.translate("developer_node", u"\u0414\u0430\u0442\u0430 \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u0430:", None))
    # retranslateUi

