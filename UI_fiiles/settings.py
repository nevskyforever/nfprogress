# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settingsuQDETT.ui'
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
    QDialogButtonBox, QGridLayout, QLabel, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QTimeEdit,
    QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(399, 477)
        font = QFont()
        font.setFamilies([u"Arial"])
        Dialog.setFont(font)
        Dialog.setStyleSheet(u"QScrollArea {\n"
"    border: none;\n"
"}")
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(Dialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFont(font)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 375, 654))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.enable_game_mode_checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.enable_game_mode_checkBox.setObjectName(u"enable_game_mode_checkBox")
        self.enable_game_mode_checkBox.setFont(font)

        self.gridLayout.addWidget(self.enable_game_mode_checkBox, 3, 0, 1, 1)

        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)

        self.label_6 = QLabel(self.scrollAreaWidgetContents)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout.addWidget(self.label_6, 12, 0, 1, 1)

        self.written_today_in_all_projects_checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.written_today_in_all_projects_checkBox.setObjectName(u"written_today_in_all_projects_checkBox")
        self.written_today_in_all_projects_checkBox.setFont(font)
        self.written_today_in_all_projects_checkBox.setTristate(False)

        self.gridLayout.addWidget(self.written_today_in_all_projects_checkBox, 8, 0, 1, 1)

        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)
        self.label_4.setWordWrap(True)

        self.gridLayout.addWidget(self.label_4, 9, 0, 1, 1)

        self.enable_global_streak_checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.enable_global_streak_checkBox.setObjectName(u"enable_global_streak_checkBox")
        self.enable_global_streak_checkBox.setFont(font)

        self.gridLayout.addWidget(self.enable_global_streak_checkBox, 0, 0, 1, 1)

        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 10, 0, 1, 1)

        self.notification_display_time_spinBox = QSpinBox(self.scrollAreaWidgetContents)
        self.notification_display_time_spinBox.setObjectName(u"notification_display_time_spinBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.notification_display_time_spinBox.sizePolicy().hasHeightForWidth())
        self.notification_display_time_spinBox.setSizePolicy(sizePolicy)
        self.notification_display_time_spinBox.setMinimum(1)
        self.notification_display_time_spinBox.setMaximum(3600)

        self.gridLayout.addWidget(self.notification_display_time_spinBox, 11, 0, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)
        self.label_3.setWordWrap(True)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 14, 0, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        self.label.setFont(font)
        self.label.setWordWrap(True)

        self.gridLayout.addWidget(self.label, 7, 0, 1, 1)

        self.enable_inf_projects_checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.enable_inf_projects_checkBox.setObjectName(u"enable_inf_projects_checkBox")
        self.enable_inf_projects_checkBox.setFont(font)

        self.gridLayout.addWidget(self.enable_inf_projects_checkBox, 5, 0, 1, 1)

        self.start_day_time = QTimeEdit(self.scrollAreaWidgetContents)
        self.start_day_time.setObjectName(u"start_day_time")
        sizePolicy.setHeightForWidth(self.start_day_time.sizePolicy().hasHeightForWidth())
        self.start_day_time.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.start_day_time, 13, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setFont(font)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", None))
        self.enable_game_mode_checkBox.setText(QCoreApplication.translate("Dialog", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p>\u041f\u043e\u0437\u0432\u043e\u043b\u044f\u0435\u0442 \u043f\u0440\u0435\u0432\u0440\u0430\u0442\u0438\u0442\u044c \u043f\u0441\u0438\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e \u0432 \u0438\u0433\u0440\u0443, \u0435\u0441\u043b\u0438 \u0432\u0430\u043c \u0441\u043b\u043e\u0436\u043d\u043e \u0441\u0435\u0431\u044f \u043c\u043e\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u0442\u044c.<br/>\u0412\u044b \u0431\u0443\u0434\u0435\u0442\u0435 \u0440\u0430\u0437\u0432\u0438\u0432\u0430\u0442\u044c \u0438\u0433\u0440\u043e\u0432\u043e\u0433\u043e \u043f\u0435\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430, \u043f\u043e\u043b\u0443\u0447\u0430\u044f \u043e\u043f\u044b\u0442 \u0438 \u043c\u043e\u043d\u0435\u0442\u044b \u0437\u0430 \u0440\u0430\u0431\u043e\u0442\u0443 \u043d\u0430\u0434 \u0442\u0435\u043a\u0441\u0442\u0430\u043c\u0438.<br/>\u0410\u043a\u0442\u0438\u0432\u0438\u0440\u0443\u0439\u0442\u0435 \u0440\u0435\u0436\u0438\u043c \u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443"
                        "\u0439\u0442\u0435 \u0441\u0430\u043c\u0438! </p></body></html>", None))
        self.label_6.setText(QCoreApplication.translate("Dialog", u"\u0412\u0440\u0435\u043c\u044f \u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u0443\u0442\u043e\u043a:", None))
        self.written_today_in_all_projects_checkBox.setText(QCoreApplication.translate("Dialog", u"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c, \u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0430\u0445", None))
        self.label_4.setText(QCoreApplication.translate("Dialog", u"\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442, \u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0432\u044b \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043d\u0430\u043f\u0438\u0441\u0430\u043b\u0438 \u0432\u043e \u0432\u0441\u0435\u0445 \u043f\u0440\u043e\u0435\u043a\u0442\u0430\u0445", None))
        self.enable_global_streak_checkBox.setText(QCoreApplication.translate("Dialog", u"\u0421\u0442\u0440\u0438\u043a\u0438", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"\u0412\u0440\u0435\u043c\u044f \u043f\u043e\u043a\u0430\u0437\u0430 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0439:", None))
        self.notification_display_time_spinBox.setSuffix(QCoreApplication.translate("Dialog", u" \u0441\u0435\u043a.", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p>\u0410\u043a\u0442\u0438\u0432\u0438\u0440\u0443\u0435\u0442 \u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a \u0438 \u0441\u0442\u0440\u0438\u043a\u0438 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0430\u0445</p><p>\u041f\u0440\u0438 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0435 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u0430 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435 \u0443 \u0432\u0430\u0441 \u0431\u0443\u0434\u0435\u0442 \u0435\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u0430\u044f \u0446\u0435\u043b\u044c, \u043f\u0440\u0438 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u0438 \u043a\u043e\u0442\u043e\u0440\u043e\u0439 \u0432\u044b \u043d\u0430\u0447\u043d\u0435\u0442\u0435 \u0438\u043b\u0438 \u043f\u0440\u043e\u0434\u043b\u0438\u0442\u0435 \u0441\u0442\u0440\u0438\u043a.</p><p>\u0421\u0442\u0440\u0438\u043a - \u0434\u0435\u043d\u044c, \u043a\u043e\u0433\u0434\u0430 \u0432\u044b \u0432\u044b\u043f\u043e\u043b\u043d\u0438"
                        "\u043b\u0438 \u0446\u0435\u043b\u044c \u043f\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0443.<br/>\u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a - \u0434\u0435\u043d\u044c, \u043a\u043e\u0433\u0434\u0430 \u0432\u044b \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u043b\u0438 \u0446\u0435\u043b\u044c \u0445\u043e\u0442\u044f \u0431\u044b \u0432 \u043e\u0434\u043d\u043e\u043c \u043f\u0440\u043e\u0435\u043a\u0442\u0435 \u0441 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u043e\u043c.</p></body></html>", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p>\u0421\u043e\u0437\u0434\u0430\u0435\u0442 \u043f\u0440\u043e\u0435\u043a\u0442 \u0441 \u0431\u0435\u0441\u043a\u043e\u043d\u0435\u0447\u043d\u043e\u0439 \u0446\u0435\u043b\u044c\u044e.</p><p>\u041f\u043e\u043b\u0435\u0437\u043d\u043e, \u0435\u0441\u043b\u0438 \u0432\u044b \u0445\u043e\u0442\u0438\u0438\u0442\u0435 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u043d\u0430\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0442\u0435\u043a\u0442\u0441\u043e\u0432, \u0434\u043b\u044f \u043a\u043e\u0442\u043e\u0440\u044b\u0445 \u043d\u0435 \u0445\u043e\u0442\u0438\u0442\u0435 \u0441\u043e\u0437\u0434\u0430\u0432\u0430\u0442\u044c \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u0440\u043e\u0435\u043a\u0442 (\u043f\u043e\u0441\u0442\u044b \u0432 \u0441\u043e\u0446. \u0441\u0435\u0442\u044f\u0445, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440), \u043d\u043e \u0445\u043e\u0442\u0438\u0442\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u044c \u043d\u0430\u0433\u0440"
                        "\u0430\u0434\u044b \u0432 \u0438\u0433\u0440\u043e\u0432\u043e\u043c \u0440\u0435\u0436\u0438\u043c\u0435.</p></body></html>", None))
        self.enable_inf_projects_checkBox.setText(QCoreApplication.translate("Dialog", u"\u0411\u0435\u043a\u043e\u043d\u0435\u0447\u043d\u044b\u0439 \u043f\u0440\u043e\u0435\u043a\u0442", None))
    # retranslateUi

