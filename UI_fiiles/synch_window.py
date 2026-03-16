# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'synch_windowFfPqWU.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QGridLayout, QSizePolicy, QSpacerItem,
    QTextEdit, QWidget)

class Ui_sych_window(object):
    def setupUi(self, sych_window):
        if not sych_window.objectName():
            sych_window.setObjectName(u"sych_window")
        sych_window.resize(400, 300)
        font = QFont()
        font.setFamilies([u"Arial"])
        sych_window.setFont(font)
        self.gridLayout = QGridLayout(sych_window)
        self.gridLayout.setObjectName(u"gridLayout")
        self.buttonBox = QDialogButtonBox(sych_window)
        self.buttonBox.setObjectName(u"buttonBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 1, 2, 1, 1)

        self.message = QTextEdit(sych_window)
        self.message.setObjectName(u"message")

        self.gridLayout.addWidget(self.message, 0, 0, 1, 3)

        self.type_of_sych_cb = QComboBox(sych_window)
        self.type_of_sych_cb.addItem("")
        self.type_of_sych_cb.addItem("")
        self.type_of_sych_cb.setObjectName(u"type_of_sych_cb")
        sizePolicy.setHeightForWidth(self.type_of_sych_cb.sizePolicy().hasHeightForWidth())
        self.type_of_sych_cb.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.type_of_sych_cb, 1, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 1, 1, 1)


        self.retranslateUi(sych_window)
        self.buttonBox.accepted.connect(sych_window.accept)
        self.buttonBox.rejected.connect(sych_window.reject)

        QMetaObject.connectSlotsByName(sych_window)
    # setupUi

    def retranslateUi(self, sych_window):
        sych_window.setWindowTitle(QCoreApplication.translate("sych_window", u"C\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f", None))
        self.type_of_sych_cb.setItemText(0, QCoreApplication.translate("sych_window", u"Word", None))
        self.type_of_sych_cb.setItemText(1, QCoreApplication.translate("sych_window", u"Scrivener", None))

    # retranslateUi

