# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'create_custom_itemFGYHXL.ui'
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

class Ui_create_castom_item(object):
    def setupUi(self, create_castom_item):
        if not create_castom_item.objectName():
            create_castom_item.setObjectName(u"create_castom_item")
        create_castom_item.resize(390, 267)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(create_castom_item.sizePolicy().hasHeightForWidth())
        create_castom_item.setSizePolicy(sizePolicy)
        font = QFont()
        font.setFamilies([u"Arial"])
        create_castom_item.setFont(font)
        self.gridLayout = QGridLayout(create_castom_item)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 0, 3, 1, 1)

        self.item_name_le = QLineEdit(create_castom_item)
        self.item_name_le.setObjectName(u"item_name_le")
        self.item_name_le.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.item_name_le, 1, 2, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 4, 2, 1, 1)

        self.label_3 = QLabel(create_castom_item)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setWordWrap(True)

        self.gridLayout.addWidget(self.label_3, 0, 1, 1, 2)

        self.item_price_le = QLineEdit(create_castom_item)
        self.item_price_le.setObjectName(u"item_price_le")
        self.item_price_le.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.item_price_le.setReadOnly(False)
        self.item_price_le.setClearButtonEnabled(False)

        self.gridLayout.addWidget(self.item_price_le, 3, 2, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(create_castom_item)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)

        self.gridLayout.addWidget(self.buttonBox, 5, 1, 1, 2)

        self.item_price_label = QLabel(create_castom_item)
        self.item_price_label.setObjectName(u"item_price_label")

        self.gridLayout.addWidget(self.item_price_label, 3, 1, 1, 1)

        self.item_name_label = QLabel(create_castom_item)
        self.item_name_label.setObjectName(u"item_name_label")

        self.gridLayout.addWidget(self.item_name_label, 1, 1, 1, 1)


        self.retranslateUi(create_castom_item)
        self.buttonBox.accepted.connect(create_castom_item.accept)
        self.buttonBox.rejected.connect(create_castom_item.reject)

        QMetaObject.connectSlotsByName(create_castom_item)
    # setupUi

    def retranslateUi(self, create_castom_item):
        create_castom_item.setWindowTitle(QCoreApplication.translate("create_castom_item", u"\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043d\u0430\u0433\u0440\u0430\u0434\u044b", None))
#if QT_CONFIG(statustip)
        self.item_name_le.setStatusTip("")
#endif // QT_CONFIG(statustip)
        self.item_name_le.setPlaceholderText(QCoreApplication.translate("create_castom_item", u"\u041f\u0435\u0447\u0435\u043d\u044c\u043a\u0430", None))
        self.label_3.setText(QCoreApplication.translate("create_castom_item", u"<html><head/><body><p>\u0412\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0441\u043e\u0431\u0441\u0442\u0432\u0435\u043d\u043d\u0443\u044e \u043d\u0430\u0433\u0440\u0430\u0434\u0443.</p><p>\u041d\u0430 \u0435\u0435 \u0446\u0435\u043d\u0443 \u043d\u0435 \u0432\u043b\u0438\u044f\u0435\u0442 \u0438\u043d\u0444\u043b\u044f\u0446\u0438\u044f \u0438 \u0443\u0440\u043e\u0432\u0435\u043d\u044c \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430.</p><p>\u041d\u0430\u0433\u0440\u0430\u0434\u044b \u043a\u043e\u043f\u044f\u0442\u0441\u044f \u0432 \u0438\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u0435 \u0438 \u043c\u043e\u0433\u0443\u0442 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f, \u043d\u043e \u043d\u0435 \u0438\u043c\u0435\u044e\u0442 \u044d\u0444\u0444\u0435\u043a\u0442\u0430.</p></body></html>", None))
        self.item_price_le.setPlaceholderText(QCoreApplication.translate("create_castom_item", u"\u0442\u043e\u043b\u044c\u043a\u043e \u0446\u0438\u0444\u0440\u044b (1.0)", None))
        self.item_price_label.setText(QCoreApplication.translate("create_castom_item", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c:", None))
        self.item_name_label.setText(QCoreApplication.translate("create_castom_item", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435:", None))
    # retranslateUi

