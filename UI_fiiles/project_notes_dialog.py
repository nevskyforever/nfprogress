# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'project_notes_dialog.ui'
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

class Ui_project_notes_dialog(object):
    def setupUi(self, project_notes_dialog):
        if not project_notes_dialog.objectName():
            project_notes_dialog.setObjectName(u"project_notes_dialog")
        project_notes_dialog.resize(1180, 760)
        project_notes_dialog.setMinimumSize(QSize(520, 480))
        font = QFont()
        font.setFamilies([u"Arial"])
        project_notes_dialog.setFont(font)
        project_notes_dialog.setSizeGripEnabled(True)
        self.verticalLayout = QVBoxLayout(project_notes_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.notes_title_label = QLabel(project_notes_dialog)
        self.notes_title_label.setObjectName(u"notes_title_label")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(16)
        font1.setBold(True)
        self.notes_title_label.setFont(font1)
        self.notes_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_title_label.setWordWrap(True)

        self.verticalLayout.addWidget(self.notes_title_label)

        self.notes_container = QWidget(project_notes_dialog)
        self.notes_container.setObjectName(u"notes_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.notes_container.sizePolicy().hasHeightForWidth())
        self.notes_container.setSizePolicy(sizePolicy)
        self.notes_container.setMinimumSize(QSize(0, 360))
        self.notes_layout = QVBoxLayout(self.notes_container)
        self.notes_layout.setObjectName(u"notes_layout")
        self.notes_layout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout.addWidget(self.notes_container)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setObjectName(u"buttons_layout")
        self.status_label = QLabel(project_notes_dialog)
        self.status_label.setObjectName(u"status_label")
        self.status_label.setWordWrap(True)

        self.buttons_layout.addWidget(self.status_label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttons_layout.addItem(self.horizontalSpacer)

        self.close_button = QPushButton(project_notes_dialog)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setMinimumSize(QSize(100, 36))

        self.buttons_layout.addWidget(self.close_button)


        self.verticalLayout.addLayout(self.buttons_layout)


        self.retranslateUi(project_notes_dialog)

        QMetaObject.connectSlotsByName(project_notes_dialog)
    # setupUi

    def retranslateUi(self, project_notes_dialog):
        project_notes_dialog.setWindowTitle(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
#if QT_CONFIG(accessibility)
        project_notes_dialog.setAccessibleName(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
#endif // QT_CONFIG(accessibility)
        self.notes_title_label.setText(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
#if QT_CONFIG(accessibility)
        self.notes_container.setAccessibleName(QCoreApplication.translate("project_notes_dialog", u"\u0420\u0435\u0434\u0430\u043a\u0442\u043e\u0440 \u0437\u0430\u043c\u0435\u0442\u043e\u043a \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
#endif // QT_CONFIG(accessibility)
        self.status_label.setText(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0437\u0430\u043c\u0435\u0442\u043e\u043a\u2026", None))
        self.close_button.setText(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u043a\u0440\u044b\u0442\u044c", None))
#if QT_CONFIG(accessibility)
        self.close_button.setAccessibleName(QCoreApplication.translate("project_notes_dialog", u"\u0417\u0430\u043a\u0440\u044b\u0442\u044c \u0437\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
#endif // QT_CONFIG(accessibility)
    # retranslateUi
