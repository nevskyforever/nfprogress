# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'synch_windowBjaQsP.ui'
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
    QTextBrowser, QWidget)

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

        self.type_of_sych_cb = QComboBox(sych_window)
        self.type_of_sych_cb.addItem("")
        self.type_of_sych_cb.addItem("")
        self.type_of_sych_cb.setObjectName(u"type_of_sych_cb")
        sizePolicy.setHeightForWidth(self.type_of_sych_cb.sizePolicy().hasHeightForWidth())
        self.type_of_sych_cb.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.type_of_sych_cb, 1, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 1, 1, 1)

        self.textBrowser = QTextBrowser(sych_window)
        self.textBrowser.setObjectName(u"textBrowser")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(13)
        self.textBrowser.setFont(font1)

        self.gridLayout.addWidget(self.textBrowser, 0, 0, 1, 3)


        self.retranslateUi(sych_window)
        self.buttonBox.accepted.connect(sych_window.accept)
        self.buttonBox.rejected.connect(sych_window.reject)

        QMetaObject.connectSlotsByName(sych_window)
    # setupUi

    def retranslateUi(self, sych_window):
        sych_window.setWindowTitle(QCoreApplication.translate("sych_window", u"C\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f", None))
        self.type_of_sych_cb.setItemText(0, QCoreApplication.translate("sych_window", u"Word", None))
        self.type_of_sych_cb.setItemText(1, QCoreApplication.translate("sych_window", u"Scrivener", None))

        self.textBrowser.setHtml(QCoreApplication.translate("sych_window", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Arial'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u044f\u0435\u0442 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u043d\u0430 \u043e\u0441\u043d\u043e\u0432"
                        "\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439 \u0432\u043e \u0432\u043d\u0435\u0448\u043d\u0435\u043c \u0444\u0430\u0439\u043b\u0435. \u041f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0441\u0430\u043c\u043e \u043f\u043e\u0434\u0441\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u0441\u0438\u043c\u0432\u043e\u043b\u044b \u0438 \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0437\u0430\u043f\u0438\u0441\u0438 \u2014 \u0432\u0430\u043c \u043d\u0435 \u043d\u0443\u0436\u043d\u043e \u0432\u0432\u043e\u0434\u0438\u0442\u044c \u0438\u0445 \u0432\u0440\u0443\u0447\u043d\u0443\u044e, \u043f\u0440\u043e\u0441\u0442\u043e \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u043d\u0443\u0436\u043d\u0443\u044e \u043a\u043d\u043e\u043f\u043a\u0443 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435.\u00a0</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; m"
                        "argin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">\u041f\u0440\u0438 \u0437\u0430\u043f\u0443\u0441\u043a\u0435 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0430\u0432\u0442\u043e\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u2014 \u0432\u0441\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0432\u043d\u043e\u0441\u044f\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px; font-weight:700;\">\u0421\u0438"
                        "\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0441 Word (.docx/.doc)</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:'Helvetica Neue'; font-size:13px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">\u0412\u044b \u043f\u0440\u0438\u0432\u044f\u0437\u044b\u0432\u0430\u0435\u0442\u0435 \u0444\u0430\u0439\u043b Word. \u041f\u0440\u0438 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u0441\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0440\u0430\u0437\u043d\u0438"
                        "\u0446\u0443 \u043a\u0430\u043a \u043d\u043e\u0432\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:'Helvetica Neue'; font-size:13px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px; font-weight:700;\">\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0441 Scrivener (.scriv)</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">\u0412\u044b \u0432\u044b\u0431\u0438"
                        "\u0440\u0430\u0435\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442 Scrivener, \u0437\u0430\u0442\u0435\u043c \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 (\u0433\u043b\u0430\u0432\u0443, \u0441\u0446\u0435\u043d\u0443). \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0435\u0442 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0432 \u044d\u0442\u043e\u043c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0435 \u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u043d\u0430\u043f\u0438\u0441\u0430\u043d\u043d\u044b\u0435 \u0441\u0438\u043c\u0432\u043e\u043b\u044b.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style"
                        "=\" font-family:'Helvetica Neue'; font-size:13px; font-weight:700;\">\u041a\u0430\u043a \u043d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c:</span><span style=\" font-family:'Helvetica Neue'; font-size:13px;\"><br /></span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">1. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0443, \u0441 \u043a\u043e\u0442\u043e\u0440\u043e\u0439 \u0432\u044b \u0445\u043e\u0442\u0438\u0442\u0435 \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e.</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">2. \u0412\u044b\u0431\u0435\u0440"
                        "\u0438\u0442\u0435 \u0444\u0430\u0439\u043b Word \u0438\u043b\u0438 \u043f\u0440\u043e\u0435\u043a\u0442 Scrivener</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Helvetica Neue'; font-size:13px;\">3. \u041f\u0440\u0438 \u0432\u044b\u0431\u043e\u0440\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 Scrivener \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u043e\u043a\u043d\u043e \u0434\u043b\u044f \u0432\u044b\u0431\u043e\u0440\u0430 \u044d\u043b\u0435\u043c\u0435\u0435\u043d\u0442\u0430 \u043f\u0440\u043e\u0435\u043a\u0442\u0430. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044d\u043b\u0435\u043c\u0435\u043d\u0442 \u0441 \u0442\u0435\u043a\u0441\u0442\u043e\u043c.</span></p></body></html>", None))
    # retranslateUi

