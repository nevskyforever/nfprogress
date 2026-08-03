# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'help_dialog.ui'
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
    QHeaderView, QSizePolicy, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_help_dialog(object):
    def setupUi(self, help_dialog):
        if not help_dialog.objectName():
            help_dialog.setObjectName(u"help_dialog")
        help_dialog.resize(980, 680)
        help_dialog.setMinimumSize(QSize(680, 460))
        font = QFont()
        font.setFamilies([u"Arial"])
        help_dialog.setFont(font)
        help_dialog.setSizeGripEnabled(True)
        self.verticalLayout = QVBoxLayout(help_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.help_splitter = QSplitter(help_dialog)
        self.help_splitter.setObjectName(u"help_splitter")
        self.help_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.help_splitter.setChildrenCollapsible(False)
        self.help_tree = QTreeWidget(self.help_splitter)
        self.help_tree.setObjectName(u"help_tree")
        self.help_tree.setMinimumSize(QSize(210, 0))
        self.help_tree.setMaximumSize(QSize(380, 16777215))
        self.help_tree.setAlternatingRowColors(True)
        self.help_tree.setHeaderHidden(True)
        self.help_splitter.addWidget(self.help_tree)
        self.help_content = QTextBrowser(self.help_splitter)
        self.help_content.setObjectName(u"help_content")
        self.help_content.setMinimumSize(QSize(360, 0))
        self.help_content.setOpenExternalLinks(True)
        self.help_splitter.addWidget(self.help_content)

        self.verticalLayout.addWidget(self.help_splitter)

        self.buttonBox = QDialogButtonBox(help_dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(help_dialog)
        self.buttonBox.rejected.connect(help_dialog.reject)

        QMetaObject.connectSlotsByName(help_dialog)
    # setupUi

    def retranslateUi(self, help_dialog):
        help_dialog.setWindowTitle(QCoreApplication.translate("help_dialog", u"\u0421\u043f\u0440\u0430\u0432\u043a\u0430", None))
        ___qtreewidgetitem = self.help_tree.headerItem()
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("help_dialog", u"\u0420\u0430\u0437\u0434\u0435\u043b\u044b \u0441\u043f\u0440\u0430\u0432\u043a\u0438", None));
    # retranslateUi
