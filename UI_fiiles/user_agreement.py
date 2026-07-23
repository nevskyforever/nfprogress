# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_agreementTrXVZX.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QSizePolicy, QTextBrowser, QVBoxLayout,
    QWidget)

class Ui_user_agreement(object):
    def setupUi(self, user_agreement):
        if not user_agreement.objectName():
            user_agreement.setObjectName(u"user_agreement")
        user_agreement.resize(750, 400)
        font = QFont()
        font.setFamilies([u"Arial"])
        user_agreement.setFont(font)
        self.verticalLayout = QVBoxLayout(user_agreement)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.textBrowser = QTextBrowser(user_agreement)
        self.textBrowser.setObjectName(u"textBrowser")
        self.textBrowser.setFont(font)

        self.verticalLayout.addWidget(self.textBrowser)

        self.agree_checkBox = QCheckBox(user_agreement)
        self.agree_checkBox.setObjectName(u"agree_checkBox")
        self.agree_checkBox.setFont(font)

        self.verticalLayout.addWidget(self.agree_checkBox)

        self.buttonBox = QDialogButtonBox(user_agreement)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setFont(font)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(user_agreement)
        self.buttonBox.accepted.connect(user_agreement.accept)
        self.buttonBox.rejected.connect(user_agreement.reject)

        QMetaObject.connectSlotsByName(user_agreement)
    # setupUi

    def retranslateUi(self, user_agreement):
        user_agreement.setWindowTitle(QCoreApplication.translate("user_agreement", u"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u043e\u0435 \u0441\u043e\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u0435", None))
        self.textBrowser.setHtml(QCoreApplication.translate("user_agreement", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Arial'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
"<h1 style=\" margin-top:18px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:xx-large; font-weight:700; color:#ffffff;\">\u0414\u041e\u041f\u041e\u041b\u041d\u0418\u0422\u0415\u041b\u042c\u041d\u042b\u0415 \u0423\u0421\u041b\u041e\u0412\u0418\u042f \u0418\u0421\u041f\u041e\u041b\u042c\u0417\u041e\u0412\u0410\u041d\u0418\u042f \u041f\u0420\u041e\u0413\u0420\u0410\u041c\u041c\u042b NFPROGRESS</span></h1>\n"
"<p style=\" margin-top:12px; margin-bottom:12"
                        "px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">\u0433. \u0421\u0430\u043c\u0430\u0440\u0430<br />23.07.2026 \u0433.</span></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700; color:#ffffff;\">1. \u041e\u0431\u0449\u0438\u0435 \u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u044f</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">1.1. \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u0434\u043b\u044f \u042d\u0412\u041c\u00a0</span><span style=\" font-weight:700; color:#ffffff;\">nfprogress</span><span style=\" color:#ffffff;\">\u00a0\u0440\u0430\u0441\u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f \u043d\u0430 \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u0445 \u043b"
                        "\u0438\u0446\u0435\u043d\u0437\u0438\u0438\u00a0</span><span style=\" font-weight:700; color:#ffffff;\">GNU General Public License version 3 (GPLv3)</span><span style=\" color:#ffffff;\">.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">1.2. \u041d\u0430\u0441\u0442\u043e\u044f\u0449\u0438\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 \u043d\u0435 \u0438\u0437\u043c\u0435\u043d\u044f\u0435\u0442 \u0438 \u043d\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0438\u0432\u0430\u0435\u0442 \u043f\u0440\u0430\u0432\u0430 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f, \u043f\u0440\u0435\u0434\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043d\u044b\u0435 \u043b\u0438\u0446\u0435\u043d\u0437\u0438\u0435\u0439 GPLv3, \u0430 \u0440\u0435\u0433\u0443\u043b\u0438\u0440\u0443\u0435\u0442 \u0438\u0441\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u043b\u044c\u043d\u043e"
                        " \u0432\u043e\u043f\u0440\u043e\u0441\u044b, \u043d\u0435 \u0443\u0440\u0435\u0433\u0443\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043d\u043e\u0439 \u043b\u0438\u0446\u0435\u043d\u0437\u0438\u0435\u0439.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">1.3. \u0412 \u0441\u043b\u0443\u0447\u0430\u0435 \u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0440\u0435\u0447\u0438\u044f \u043c\u0435\u0436\u0434\u0443 \u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0438\u043c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u043e\u043c \u0438 GPLv3 \u043f\u0440\u0438\u043c\u0435\u043d\u044f\u044e\u0442\u0441\u044f \u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u044f GPLv3.</span></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight"
                        ":700; color:#ffffff;\">2. \u0418\u043d\u0442\u0435\u043b\u043b\u0435\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u043e\u0431\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u044c</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">2.1. \u0418\u0441\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u043f\u0440\u0430\u0432\u0430 \u043d\u0430 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0443 \u043f\u0440\u0438\u043d\u0430\u0434\u043b\u0435\u0436\u0430\u0442 \u041a\u0438\u0448\u043e\u0447\u043a\u0438\u043d\u0443 \u0420\u043e\u043c\u0430\u043d\u0443 \u0420\u0443\u0441\u043b\u0430\u043d\u043e\u0432\u0438\u0447\u0443.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">2.2. \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u0440"
                        "\u0430\u0441\u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f \u043d\u0430 \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u0445 GPLv3, \u0432\u043a\u043b\u044e\u0447\u0430\u044f \u043f\u0440\u0430\u0432\u043e \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f:</span></p>\n"
"<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;\">\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0443;</li>\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0438\u0437\u0443\u0447\u0430\u0442\u044c \u0435\u0435 \u0440\u0430\u0431\u043e\u0442\u0443;</li>\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:0"
                        "px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0438\u0437\u043c\u0435\u043d\u044f\u0442\u044c \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u043a\u043e\u0434;</li>\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:0px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0440\u0430\u0441\u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u044f\u0442\u044c \u043e\u0440\u0438\u0433\u0438\u043d\u0430\u043b\u044c\u043d\u044b\u0435 \u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u043d\u044b\u0435 \u0432\u0435\u0440\u0441\u0438\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b \u043f\u0440\u0438 \u0441\u043e\u0431\u043b\u044e\u0434\u0435\u043d\u0438\u0438 \u0443\u0441\u043b\u043e\u0432\u0438\u0439 GPLv3.</li></ul>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700; color:#ffffff;\""
                        ">3. \u041f\u0435\u0440\u0441\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">3.1. \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u043d\u0435 \u043f\u0440\u0435\u0434\u0443\u0441\u043c\u0430\u0442\u0440\u0438\u0432\u0430\u0435\u0442 \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439 \u0438 \u043d\u0435 \u0441\u043e\u0431\u0438\u0440\u0430\u0435\u0442 \u0438\u043c\u044f, \u0430\u0434\u0440\u0435\u0441 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u043e\u0439 \u043f\u043e\u0447\u0442\u044b \u0438\u043b\u0438 \u0438\u043d\u044b\u0435 \u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u0446\u0438\u0440\u0443\u044e\u0449\u0438\u0435 \u0441\u0432\u0435\u0434\u0435\u043d\u0438\u044f.</span></p>\n"
"<p sty"
                        "le=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">3.2. \u041f\u0440\u0438 \u0440\u0430\u0431\u043e\u0442\u0435 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b \u043c\u043e\u0436\u0435\u0442 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u043f\u0435\u0440\u0435\u0434\u0430\u0432\u0430\u0442\u044c\u0441\u044f \u0442\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f, \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u0430\u044f \u0434\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0439 \u0438 \u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0438 \u043e\u0448\u0438\u0431\u043e\u043a, \u0432\u043a\u043b\u044e\u0447\u0430\u044f:</span></p>\n"
"<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: "
                        "0px; -qt-list-indent: 1;\">\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0432\u0435\u0440\u0441\u0438\u044e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b;</li>\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0432\u0435\u0440\u0441\u0438\u044e \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u043e\u0439 \u0441\u0438\u0441\u0442\u0435\u043c\u044b;</li>\n"
"<li style=\" color:#ffffff;\" style=\" margin-top:0px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\u0441\u0432\u0435\u0434\u0435\u043d\u0438\u044f \u043e \u0432\u043e\u0437\u043d\u0438\u043a\u0448\u0438\u0445 \u043e\u0448\u0438\u0431\u043a\u0430\u0445.</li></ul>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-inde"
                        "nt:0px;\"><span style=\" color:#ffffff;\">3.3. \u0423\u043a\u0430\u0437\u0430\u043d\u043d\u0430\u044f \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u0438\u0441\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u0434\u043b\u044f \u043e\u0431\u0435\u0441\u043f\u0435\u0447\u0435\u043d\u0438\u044f \u0440\u0430\u0431\u043e\u0442\u043e\u0441\u043f\u043e\u0441\u043e\u0431\u043d\u043e\u0441\u0442\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b \u0438 \u043d\u0435 \u043f\u0440\u0438\u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f \u0434\u043b\u044f \u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u0438 \u043b\u0438\u0447\u043d\u043e\u0441\u0442\u0438 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f.</span></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font"
                        "-size:x-large; font-weight:700; color:#ffffff;\">4. \u041e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0439</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">4.1. \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0430 \u043f\u0440\u0435\u0434\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442\u0441\u044f\u00a0</span><span style=\" font-weight:700; color:#ffffff;\">\u00ab\u043a\u0430\u043a \u0435\u0441\u0442\u044c\u00bb (AS IS)</span><span style=\" color:#ffffff;\">.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">4.2. \u0412 \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0439 \u0441\u0442\u0435\u043f\u0435\u043d\u0438, \u0434\u043e\u043f\u0443\u0441\u043a\u0430\u0435\u043c\u043e\u0439 \u043f\u0440"
                        "\u0438\u043c\u0435\u043d\u0438\u043c\u044b\u043c \u0437\u0430\u043a\u043e\u043d\u043e\u0434\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e\u043c, \u041f\u0440\u0430\u0432\u043e\u043e\u0431\u043b\u0430\u0434\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u043f\u0440\u0435\u0434\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u043a\u0430\u043a\u0438\u0445-\u043b\u0438\u0431\u043e \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0439 \u0432 \u043e\u0442\u043d\u043e\u0448\u0435\u043d\u0438\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b, \u0432\u043a\u043b\u044e\u0447\u0430\u044f \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0438 \u043f\u0440\u0438\u0433\u043e\u0434\u043d\u043e\u0441\u0442\u0438 \u0434\u043b\u044f \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\u0439 \u0446\u0435\u043b\u0438, \u0431\u0435\u0441\u043f\u0435\u0440\u0435\u0431\u043e\u0439\u043d\u043e\u0439 \u0440\u0430\u0431\u043e\u0442\u044b \u0438 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u044f \u043e\u0448\u0438"
                        "\u0431\u043e\u043a.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">4.3. \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u043e \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0435\u0442 \u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u043e\u0431 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0438 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b \u0438 \u043d\u0435\u0441\u0435\u0442 \u0441\u0432\u044f\u0437\u0430\u043d\u043d\u044b\u0435 \u0441 \u044d\u0442\u0438\u043c \u0440\u0438\u0441\u043a\u0438.</span></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700; color:#ffffff;\">5. \u041e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438"
                        "\u0435 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">5.1. \u0412 \u043f\u0440\u0435\u0434\u0435\u043b\u0430\u0445, \u0434\u043e\u043f\u0443\u0441\u043a\u0430\u0435\u043c\u044b\u0445 \u0437\u0430\u043a\u043e\u043d\u043e\u0434\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e\u043c \u0420\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u043e\u0439 \u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u0438, \u041f\u0440\u0430\u0432\u043e\u043e\u0431\u043b\u0430\u0434\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u043d\u0435\u0441\u0435\u0442 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438 \u0437\u0430 \u043b\u044e\u0431\u044b\u0435 \u0443\u0431\u044b\u0442\u043a\u0438, \u0432\u043e\u0437\u043d\u0438\u043a\u0448\u0438\u0435 \u0432\u0441\u043b\u0435\u0434\u0441\u0442\u0432"
                        "\u0438\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u044f \u043b\u0438\u0431\u043e \u043d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e\u0441\u0442\u0438 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u044f \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">5.2. \u041d\u0430\u0441\u0442\u043e\u044f\u0449\u0438\u0439 \u043f\u0443\u043d\u043a\u0442 \u043d\u0435 \u043f\u0440\u0438\u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f \u0432 \u0441\u043b\u0443\u0447\u0430\u044f\u0445, \u043a\u043e\u0433\u0434\u0430 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u044c \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0430 \u0437\u0430\u043a\u043e\u043d\u043e\u043c.</span>"
                        "</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700; color:#ffffff;\">6. \u041f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u043e\u0435 \u043f\u0440\u0430\u0432\u043e</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">6.1. \u041a \u0432\u043e\u043f\u0440\u043e\u0441\u0430\u043c, \u043d\u0435 \u0443\u0440\u0435\u0433\u0443\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u043c GPLv3, \u043f\u0440\u0438\u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f \u0437\u0430\u043a\u043e\u043d\u043e\u0434\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e \u0420\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u043e\u0439 \u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u0438.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-b"
                        "lock-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">6.2. \u0414\u043e \u043e\u0431\u0440\u0430\u0449\u0435\u043d\u0438\u044f \u0432 \u0441\u0443\u0434 \u0441\u0442\u043e\u0440\u043e\u043d\u044b \u0441\u0442\u0440\u0435\u043c\u044f\u0442\u0441\u044f \u0443\u0440\u0435\u0433\u0443\u043b\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u043f\u043e\u0440 \u043f\u0443\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u0433\u043e\u0432\u043e\u0440\u043e\u0432.</span></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700; color:#ffffff;\">7. \u041a\u043e\u043d\u0442\u0430\u043a\u0442\u044b</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">\u041f\u0440\u0430\u0432\u043e\u043e\u0431\u043b\u0430\u0434\u0430\u0442\u0435\u043b\u044c:</span></p>\n"
"<p style=\" margin-top"
                        ":12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">\u041a\u0438\u0448\u043e\u0447\u043a\u0438\u043d \u0420\u043e\u043c\u0430\u043d \u0420\u0443\u0441\u043b\u0430\u043d\u043e\u0432\u0438\u0447</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ffffff;\">\u042d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u0430\u044f \u043f\u043e\u0447\u0442\u0430:\u00a0</span><span style=\" font-weight:700; color:#ffffff;\">app@nfpr.ru</span></p></body></html>", None))
        self.agree_checkBox.setText(QCoreApplication.translate("user_agreement", u"\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u0435\u044e, \u0447\u0442\u043e \u043e\u0437\u043d\u0430\u0430\u043a\u043e\u043c\u0438\u043b\u0441\u044f \u0441 \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u043c\u0438 \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u043e\u0433\u043e \u0441\u043e\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u044f \u0438 \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u044e \u0438\u0445", None))
    # retranslateUi

