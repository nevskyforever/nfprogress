# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mindmap_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_mindmap_dialog(object):
    def setupUi(self, mindmap_dialog):
        if not mindmap_dialog.objectName():
            mindmap_dialog.setObjectName(u"mindmap_dialog")
        mindmap_dialog.resize(1100, 720)
        mindmap_dialog.setMinimumSize(QSize(700, 480))
        font = QFont()
        font.setFamilies([u"Arial"])
        mindmap_dialog.setFont(font)
        mindmap_dialog.setSizeGripEnabled(True)
        self.verticalLayout = QVBoxLayout(mindmap_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.map_title_label = QLabel(mindmap_dialog)
        self.map_title_label.setObjectName(u"map_title_label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(16)
        font1.setBold(True)
        self.map_title_label.setFont(font1)
        self.map_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_title_label.setWordWrap(True)

        self.verticalLayout.addWidget(self.map_title_label)

        self.instructions_label = QLabel(mindmap_dialog)
        self.instructions_label.setObjectName(u"instructions_label")
        self.instructions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instructions_label.setWordWrap(True)

        self.verticalLayout.addWidget(self.instructions_label)

        self.mindmap_container = QWidget(mindmap_dialog)
        self.mindmap_container.setObjectName(u"mindmap_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.mindmap_container.sizePolicy().hasHeightForWidth())
        self.mindmap_container.setSizePolicy(sizePolicy)
        self.mindmap_container.setMinimumSize(QSize(0, 360))
        self.mindmap_layout = QVBoxLayout(self.mindmap_container)
        self.mindmap_layout.setObjectName(u"mindmap_layout")
        self.mindmap_layout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout.addWidget(self.mindmap_container)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setObjectName(u"buttons_layout")
        self.save_status_label = QLabel(mindmap_dialog)
        self.save_status_label.setObjectName(u"save_status_label")
        self.save_status_label.setWordWrap(True)

        self.buttons_layout.addWidget(self.save_status_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttons_layout.addItem(self.horizontalSpacer)

        self.add_free_node_button = QPushButton(mindmap_dialog)
        self.add_free_node_button.setObjectName(u"add_free_node_button")

        self.buttons_layout.addWidget(self.add_free_node_button)

        self.add_note_button = QPushButton(mindmap_dialog)
        self.add_note_button.setObjectName(u"add_note_button")

        self.buttons_layout.addWidget(self.add_note_button)

        self.save_button = QPushButton(mindmap_dialog)
        self.save_button.setObjectName(u"save_button")

        self.buttons_layout.addWidget(self.save_button)

        self.export_button = QPushButton(mindmap_dialog)
        self.export_button.setObjectName(u"export_button")

        self.buttons_layout.addWidget(self.export_button)

        self.close_button = QPushButton(mindmap_dialog)
        self.close_button.setObjectName(u"close_button")

        self.buttons_layout.addWidget(self.close_button)


        self.verticalLayout.addLayout(self.buttons_layout)

        QWidget.setTabOrder(self.add_free_node_button, self.add_note_button)
        QWidget.setTabOrder(self.add_note_button, self.save_button)
        QWidget.setTabOrder(self.save_button, self.export_button)
        QWidget.setTabOrder(self.export_button, self.close_button)

        self.retranslateUi(mindmap_dialog)

        QMetaObject.connectSlotsByName(mindmap_dialog)
    # setupUi

    def retranslateUi(self, mindmap_dialog):
        mindmap_dialog.setWindowTitle(QCoreApplication.translate("mindmap_dialog", u"\u041a\u0430\u0440\u0442\u0430", None))
#if QT_CONFIG(accessibility)
        mindmap_dialog.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u041a\u0430\u0440\u0442\u0430 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u0438\u043b\u0438 \u044d\u0442\u0430\u043f\u0430", None))
#endif // QT_CONFIG(accessibility)
        self.map_title_label.setText(QCoreApplication.translate("mindmap_dialog", u"\u041a\u0430\u0440\u0442\u0430 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u0438\u043b\u0438 \u044d\u0442\u0430\u043f\u0430", None))
        self.instructions_label.setText(QCoreApplication.translate("mindmap_dialog", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0443\u0437\u0435\u043b: Tab \u2014 \u0434\u043e\u0447\u0435\u0440\u043d\u0438\u0439, Enter \u2014 \u0441\u043e\u0441\u0435\u0434\u043d\u0438\u0439, F2 \u2014 \u0438\u0437\u043c\u0435\u043d\u0438\u0442\u044c, Delete \u2014 \u0443\u0434\u0430\u043b\u0438\u0442\u044c. \u041a\u0430\u0440\u0442\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438.", None))
#if QT_CONFIG(accessibility)
        self.mindmap_container.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u0420\u0435\u0434\u0430\u043a\u0442\u043e\u0440 \u043a\u0430\u0440\u0442\u044b", None))
#endif // QT_CONFIG(accessibility)
        self.save_status_label.setText(QCoreApplication.translate("mindmap_dialog", u"\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u0430\u0440\u0442\u044b\u2026", None))
        self.add_free_node_button.setText(QCoreApplication.translate("mindmap_dialog", u"\u0421\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0439 \u0443\u0437\u0435\u043b", None))
#if QT_CONFIG(accessibility)
        self.add_free_node_button.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0439 \u0443\u0437\u0435\u043b", None))
#endif // QT_CONFIG(accessibility)
        self.add_note_button.setText(QCoreApplication.translate("mindmap_dialog", u"\u0417\u0430\u043c\u0435\u0442\u043a\u0430", None))
#if QT_CONFIG(accessibility)
        self.add_note_button.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043b\u0430\u0432\u0430\u044e\u0449\u0443\u044e \u0437\u0430\u043c\u0435\u0442\u043a\u0443", None))
#endif // QT_CONFIG(accessibility)
        self.save_button.setText(QCoreApplication.translate("mindmap_dialog", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", None))
#if QT_CONFIG(accessibility)
        self.save_button.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043a\u0430\u0440\u0442\u0443", None))
#endif // QT_CONFIG(accessibility)
        self.export_button.setText(QCoreApplication.translate("mindmap_dialog", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442", None))
#if QT_CONFIG(accessibility)
        self.export_button.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043a\u0430\u0440\u0442\u0443", None))
#endif // QT_CONFIG(accessibility)
        self.close_button.setText(QCoreApplication.translate("mindmap_dialog", u"\u0417\u0430\u043a\u0440\u044b\u0442\u044c", None))
#if QT_CONFIG(accessibility)
        self.close_button.setAccessibleName(QCoreApplication.translate("mindmap_dialog", u"\u0417\u0430\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0440\u0442\u0443", None))
#endif // QT_CONFIG(accessibility)
    # retranslateUi
