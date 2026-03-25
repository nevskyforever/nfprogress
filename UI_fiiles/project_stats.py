# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'project_statsqAufgE.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(397, 488)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(Dialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 371, 462))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.stat_best_day = QLabel(self.scrollAreaWidgetContents)
        self.stat_best_day.setObjectName(u"stat_best_day")

        self.gridLayout.addWidget(self.stat_best_day, 6, 1, 1, 1)

        self.stat_current_streak = QLabel(self.scrollAreaWidgetContents)
        self.stat_current_streak.setObjectName(u"stat_current_streak")

        self.gridLayout.addWidget(self.stat_current_streak, 8, 1, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label_3.setWordWrap(True)

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.label_13 = QLabel(self.scrollAreaWidgetContents)
        self.label_13.setObjectName(u"label_13")

        self.gridLayout.addWidget(self.label_13, 1, 0, 1, 1)

        self.stat_avg_symbols_per_note = QLabel(self.scrollAreaWidgetContents)
        self.stat_avg_symbols_per_note.setObjectName(u"stat_avg_symbols_per_note")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.stat_avg_symbols_per_note.sizePolicy().hasHeightForWidth())
        self.stat_avg_symbols_per_note.setSizePolicy(sizePolicy)
        self.stat_avg_symbols_per_note.setWordWrap(True)

        self.gridLayout.addWidget(self.stat_avg_symbols_per_note, 3, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 13, 0, 1, 1)

        self.label_20 = QLabel(self.scrollAreaWidgetContents)
        self.label_20.setObjectName(u"label_20")

        self.gridLayout.addWidget(self.label_20, 10, 0, 1, 1)

        self.stat_avg_symbols_per_active_day = QLabel(self.scrollAreaWidgetContents)
        self.stat_avg_symbols_per_active_day.setObjectName(u"stat_avg_symbols_per_active_day")

        self.gridLayout.addWidget(self.stat_avg_symbols_per_active_day, 2, 1, 1, 1)

        self.stat_freezes_used = QLabel(self.scrollAreaWidgetContents)
        self.stat_freezes_used.setObjectName(u"stat_freezes_used")
        sizePolicy.setHeightForWidth(self.stat_freezes_used.sizePolicy().hasHeightForWidth())
        self.stat_freezes_used.setSizePolicy(sizePolicy)
        self.stat_freezes_used.setWordWrap(True)

        self.gridLayout.addWidget(self.stat_freezes_used, 5, 1, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label.setWordWrap(True)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.stat_notes_count = QLabel(self.scrollAreaWidgetContents)
        self.stat_notes_count.setObjectName(u"stat_notes_count")
        sizePolicy.setHeightForWidth(self.stat_notes_count.sizePolicy().hasHeightForWidth())
        self.stat_notes_count.setSizePolicy(sizePolicy)
        self.stat_notes_count.setWordWrap(True)

        self.gridLayout.addWidget(self.stat_notes_count, 0, 1, 1, 1)

        self.label_9 = QLabel(self.scrollAreaWidgetContents)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setWordWrap(True)

        self.gridLayout.addWidget(self.label_9, 6, 0, 1, 1)

        self.label_15 = QLabel(self.scrollAreaWidgetContents)
        self.label_15.setObjectName(u"label_15")

        self.gridLayout.addWidget(self.label_15, 2, 0, 1, 1)

        self.label_21 = QLabel(self.scrollAreaWidgetContents)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setWordWrap(True)

        self.gridLayout.addWidget(self.label_21, 11, 0, 1, 1)

        self.stat_total_in_unit = QLabel(self.scrollAreaWidgetContents)
        self.stat_total_in_unit.setObjectName(u"stat_total_in_unit")

        self.gridLayout.addWidget(self.stat_total_in_unit, 1, 1, 1, 1)

        self.label_19 = QLabel(self.scrollAreaWidgetContents)
        self.label_19.setObjectName(u"label_19")

        self.gridLayout.addWidget(self.label_19, 9, 0, 1, 1)

        self.label_17 = QLabel(self.scrollAreaWidgetContents)
        self.label_17.setObjectName(u"label_17")

        self.gridLayout.addWidget(self.label_17, 8, 0, 1, 1)

        self.label_7 = QLabel(self.scrollAreaWidgetContents)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label_7.setWordWrap(True)

        self.gridLayout.addWidget(self.label_7, 5, 0, 1, 1)

        self.stat_best_weekday = QLabel(self.scrollAreaWidgetContents)
        self.stat_best_weekday.setObjectName(u"stat_best_weekday")
        self.stat_best_weekday.setWordWrap(True)

        self.gridLayout.addWidget(self.stat_best_weekday, 7, 1, 1, 1)

        self.label_11 = QLabel(self.scrollAreaWidgetContents)
        self.label_11.setObjectName(u"label_11")

        self.gridLayout.addWidget(self.label_11, 7, 0, 1, 1)

        self.stat_avg_notes_per_day = QLabel(self.scrollAreaWidgetContents)
        self.stat_avg_notes_per_day.setObjectName(u"stat_avg_notes_per_day")
        sizePolicy.setHeightForWidth(self.stat_avg_notes_per_day.sizePolicy().hasHeightForWidth())
        self.stat_avg_notes_per_day.setSizePolicy(sizePolicy)
        self.stat_avg_notes_per_day.setWordWrap(True)

        self.gridLayout.addWidget(self.stat_avg_notes_per_day, 4, 1, 1, 1)

        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.label_5.setWordWrap(True)

        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)

        self.label_22 = QLabel(self.scrollAreaWidgetContents)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setWordWrap(True)

        self.gridLayout.addWidget(self.label_22, 12, 0, 1, 1)

        self.stat_max_streak = QLabel(self.scrollAreaWidgetContents)
        self.stat_max_streak.setObjectName(u"stat_max_streak")

        self.gridLayout.addWidget(self.stat_max_streak, 9, 1, 1, 1)

        self.stat_days_since_start = QLabel(self.scrollAreaWidgetContents)
        self.stat_days_since_start.setObjectName(u"stat_days_since_start")

        self.gridLayout.addWidget(self.stat_days_since_start, 10, 1, 1, 1)

        self.stat_active_days_count = QLabel(self.scrollAreaWidgetContents)
        self.stat_active_days_count.setObjectName(u"stat_active_days_count")

        self.gridLayout.addWidget(self.stat_active_days_count, 11, 1, 1, 1)

        self.stat_active_days_percent = QLabel(self.scrollAreaWidgetContents)
        self.stat_active_days_percent.setObjectName(u"stat_active_days_percent")

        self.gridLayout.addWidget(self.stat_active_days_percent, 12, 1, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.stat_best_day.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.stat_current_streak.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"\u0421\u0440\u0435\u0434\u043d\u0435\u0435 \u043a\u043e\u043b-\u0432\u043e \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0432 \u0437\u0430\u043f\u0438\u0441\u0438:", None))
        self.label_13.setText(QCoreApplication.translate("Dialog", u"\u0412\u0441\u0435\u0433\u043e \u043d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0432 \u0435\u0434\u0438\u043d\u0438\u0446\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u0430:", None))
        self.stat_avg_symbols_per_note.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_20.setText(QCoreApplication.translate("Dialog", u"\u0414\u043d\u0435\u0439 \u0441 \u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u0440\u043e\u0435\u043a\u0442\u0430:", None))
        self.stat_avg_symbols_per_active_day.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.stat_freezes_used.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"\u041a\u043e\u043b-\u0432\u043e \u0437\u0430\u043f\u0438\u0441\u0435\u0439:", None))
        self.stat_notes_count.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_9.setText(QCoreApplication.translate("Dialog", u"\u041b\u0443\u0447\u0448\u0438\u0439 \u0434\u0435\u043d\u044c (\u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0437\u0430 \u043e\u0434\u043d\u0443 \u0434\u0430\u0442\u0443):", None))
        self.label_15.setText(QCoreApplication.translate("Dialog", u"\u0421\u0440\u0435\u0434\u043d\u0435\u0435 \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432 \u0432 \u0434\u0435\u043d\u044c:", None))
        self.label_21.setText(QCoreApplication.translate("Dialog", u"\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0434\u043d\u0435\u0439 (\u0434\u043d\u0435\u0439, \u043a\u043e\u0433\u0434\u0430 \u0431\u044b\u043b\u0430 \u0445\u043e\u0442\u044c \u043e\u0434\u043d\u0430 \u0437\u0430\u043f\u0438\u0441\u044c):", None))
        self.stat_total_in_unit.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_19.setText(QCoreApplication.translate("Dialog", u"\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a:", None))
        self.label_17.setText(QCoreApplication.translate("Dialog", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a (\u0434\u043d\u0435\u0439):", None))
        self.label_7.setText(QCoreApplication.translate("Dialog", u"\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u043e \u0437\u0430\u043c\u043e\u0440\u043e\u0437\u043e\u043a:", None))
        self.stat_best_weekday.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_11.setText(QCoreApplication.translate("Dialog", u"\u0421\u0430\u043c\u044b\u0439 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0434\u0435\u043d\u044c \u043d\u0435\u0434\u0435\u043b\u0438:", None))
        self.stat_avg_notes_per_day.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"\u0421\u0440\u0435\u0434\u043d\u0435\u0435 \u043a\u043e\u043b-\u0432\u043e \u0437\u0430\u043f\u0438\u0441\u0435\u0439 \u0432 \u0434\u0435\u043d\u044c:", None))
        self.label_22.setText(QCoreApplication.translate("Dialog", u"\u041f\u0440\u043e\u0446\u0435\u043d\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0434\u043d\u0435\u0439 \u043e\u0442 \u043e\u0431\u0449\u0435\u0433\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430:", None))
        self.stat_max_streak.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.stat_days_since_start.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.stat_active_days_count.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.stat_active_days_percent.setText(QCoreApplication.translate("Dialog", u"\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
    # retranslateUi

