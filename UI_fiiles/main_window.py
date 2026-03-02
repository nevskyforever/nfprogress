# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_windowVaNpgn.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QTabWidget, QVBoxLayout, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(733, 620)
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        main_window.setFont(font)
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(-1, 10, 731, 611))
        self.projects_tab = QWidget()
        self.projects_tab.setObjectName(u"projects_tab")
        self.btns_create_filter = QWidget(self.projects_tab)
        self.btns_create_filter.setObjectName(u"btns_create_filter")
        self.btns_create_filter.setGeometry(QRect(10, 0, 219, 61))
        self.btns_create_filter.setFont(font)
        self.horizontalLayout_4 = QHBoxLayout(self.btns_create_filter)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.btn_create_project = QPushButton(self.btns_create_filter)
        self.btn_create_project.setObjectName(u"btn_create_project")
        self.btn_create_project.setFont(font)

        self.horizontalLayout_4.addWidget(self.btn_create_project)

        self.filter_project_box = QComboBox(self.btns_create_filter)
        self.filter_project_box.addItem("")
        self.filter_project_box.addItem("")
        self.filter_project_box.addItem("")
        self.filter_project_box.setObjectName(u"filter_project_box")

        self.horizontalLayout_4.addWidget(self.filter_project_box)

        self.project_detail_widget = QWidget(self.projects_tab)
        self.project_detail_widget.setObjectName(u"project_detail_widget")
        self.project_detail_widget.setGeometry(QRect(220, 20, 501, 551))
        self.project_info = QGroupBox(self.project_detail_widget)
        self.project_info.setObjectName(u"project_info")
        self.project_info.setEnabled(True)
        self.project_info.setGeometry(QRect(10, 40, 331, 301))
        self.project_info.setFont(font)
        self.project_info.setFlat(False)
        self.formLayout_2 = QFormLayout(self.project_info)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setLabelAlignment(Qt.AlignmentFlag.AlignJustify|Qt.AlignmentFlag.AlignVCenter)
        self.formLayout_2.setContentsMargins(2, -1, -1, -1)
        self.label_status = QLabel(self.project_info)
        self.label_status.setObjectName(u"label_status")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_status)

        self.status = QLabel(self.project_info)
        self.status.setObjectName(u"status")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.status)

        self.label_progress = QLabel(self.project_info)
        self.label_progress.setObjectName(u"label_progress")

        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_progress)

        self.progress = QLabel(self.project_info)
        self.progress.setObjectName(u"progress")

        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.FieldRole, self.progress)

        self.label_goal = QLabel(self.project_info)
        self.label_goal.setObjectName(u"label_goal")

        self.formLayout_2.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_goal)

        self.goal = QLabel(self.project_info)
        self.goal.setObjectName(u"goal")

        self.formLayout_2.setWidget(4, QFormLayout.ItemRole.FieldRole, self.goal)

        self.label_total = QLabel(self.project_info)
        self.label_total.setObjectName(u"label_total")

        self.formLayout_2.setWidget(5, QFormLayout.ItemRole.LabelRole, self.label_total)

        self.total = QLabel(self.project_info)
        self.total.setObjectName(u"total")

        self.formLayout_2.setWidget(5, QFormLayout.ItemRole.FieldRole, self.total)

        self.label_today_added = QLabel(self.project_info)
        self.label_today_added.setObjectName(u"label_today_added")

        self.formLayout_2.setWidget(6, QFormLayout.ItemRole.LabelRole, self.label_today_added)

        self.added_today = QLabel(self.project_info)
        self.added_today.setObjectName(u"added_today")

        self.formLayout_2.setWidget(6, QFormLayout.ItemRole.FieldRole, self.added_today)

        self.label_need = QLabel(self.project_info)
        self.label_need.setObjectName(u"label_need")

        self.formLayout_2.setWidget(7, QFormLayout.ItemRole.LabelRole, self.label_need)

        self.need = QLabel(self.project_info)
        self.need.setObjectName(u"need")

        self.formLayout_2.setWidget(7, QFormLayout.ItemRole.FieldRole, self.need)

        self.label_deadline = QLabel(self.project_info)
        self.label_deadline.setObjectName(u"label_deadline")

        self.formLayout_2.setWidget(8, QFormLayout.ItemRole.LabelRole, self.label_deadline)

        self.deadline = QLabel(self.project_info)
        self.deadline.setObjectName(u"deadline")

        self.formLayout_2.setWidget(8, QFormLayout.ItemRole.FieldRole, self.deadline)

        self.label_streaks = QLabel(self.project_info)
        self.label_streaks.setObjectName(u"label_streaks")

        self.formLayout_2.setWidget(9, QFormLayout.ItemRole.LabelRole, self.label_streaks)

        self.streaks = QLabel(self.project_info)
        self.streaks.setObjectName(u"streaks")

        self.formLayout_2.setWidget(9, QFormLayout.ItemRole.FieldRole, self.streaks)

        self.label_streak_status = QLabel(self.project_info)
        self.label_streak_status.setObjectName(u"label_streak_status")

        self.formLayout_2.setWidget(10, QFormLayout.ItemRole.LabelRole, self.label_streak_status)

        self.streak_status = QLabel(self.project_info)
        self.streak_status.setObjectName(u"streak_status")

        self.formLayout_2.setWidget(10, QFormLayout.ItemRole.FieldRole, self.streak_status)

        self.label_max_streak = QLabel(self.project_info)
        self.label_max_streak.setObjectName(u"label_max_streak")

        self.formLayout_2.setWidget(11, QFormLayout.ItemRole.LabelRole, self.label_max_streak)

        self.max_streak = QLabel(self.project_info)
        self.max_streak.setObjectName(u"max_streak")

        self.formLayout_2.setWidget(11, QFormLayout.ItemRole.FieldRole, self.max_streak)

        self.last_note = QLabel(self.project_info)
        self.last_note.setObjectName(u"last_note")

        self.formLayout_2.setWidget(12, QFormLayout.ItemRole.LabelRole, self.last_note)

        self.l = QLabel(self.project_info)
        self.l.setObjectName(u"l")

        self.formLayout_2.setWidget(12, QFormLayout.ItemRole.FieldRole, self.l)

        self.name_selected_project = QLabel(self.project_detail_widget)
        self.name_selected_project.setObjectName(u"name_selected_project")
        self.name_selected_project.setGeometry(QRect(110, 10, 281, 31))
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(20)
        self.name_selected_project.setFont(font1)
        self.name_selected_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.change_project_widget = QWidget(self.project_detail_widget)
        self.change_project_widget.setObjectName(u"change_project_widget")
        self.change_project_widget.setEnabled(False)
        self.change_project_widget.setGeometry(QRect(360, 60, 111, 281))
        self.change_project_widget.setFont(font)
        self.verticalLayout_3 = QVBoxLayout(self.change_project_widget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.btn_complete_project = QPushButton(self.change_project_widget)
        self.btn_complete_project.setObjectName(u"btn_complete_project")
        self.btn_complete_project.setEnabled(False)
        self.btn_complete_project.setFont(font)

        self.verticalLayout_3.addWidget(self.btn_complete_project)

        self.btn_archived_project = QPushButton(self.change_project_widget)
        self.btn_archived_project.setObjectName(u"btn_archived_project")
        self.btn_archived_project.setEnabled(False)
        self.btn_archived_project.setFont(font)

        self.verticalLayout_3.addWidget(self.btn_archived_project)

        self.btn_delete_project = QPushButton(self.change_project_widget)
        self.btn_delete_project.setObjectName(u"btn_delete_project")
        self.btn_delete_project.setEnabled(False)

        self.verticalLayout_3.addWidget(self.btn_delete_project)

        self.btn_change_project = QPushButton(self.change_project_widget)
        self.btn_change_project.setObjectName(u"btn_change_project")
        self.btn_change_project.setEnabled(False)

        self.verticalLayout_3.addWidget(self.btn_change_project)

        self.note_widget = QWidget(self.project_detail_widget)
        self.note_widget.setObjectName(u"note_widget")
        self.note_widget.setGeometry(QRect(9, 359, 491, 171))
        self.label_3 = QLabel(self.note_widget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(-10, 40, 491, 20))
        font2 = QFont()
        font2.setFamilies([u"Arial"])
        font2.setPointSize(16)
        self.label_3.setFont(font2)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_scroll = QScrollArea(self.note_widget)
        self.note_scroll.setObjectName(u"note_scroll")
        self.note_scroll.setGeometry(QRect(0, 70, 481, 101))
        self.note_scroll.setFont(font)
        self.note_scroll.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 479, 99))
        self.note_scroll.setWidget(self.scrollAreaWidgetContents_3)
        self.flash_note = QWidget(self.note_widget)
        self.flash_note.setObjectName(u"flash_note")
        self.flash_note.setGeometry(QRect(70, 0, 351, 45))
        self.flash_note.setFont(font)
        self.gridLayout = QGridLayout(self.flash_note)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_9 = QLabel(self.flash_note)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 0, 0, 1, 1)

        self.pb_save_flash_note = QPushButton(self.flash_note)
        self.pb_save_flash_note.setObjectName(u"pb_save_flash_note")
        self.pb_save_flash_note.setEnabled(False)

        self.gridLayout.addWidget(self.pb_save_flash_note, 0, 2, 1, 1)

        self.new_symbols = QLineEdit(self.flash_note)
        self.new_symbols.setObjectName(u"new_symbols")

        self.gridLayout.addWidget(self.new_symbols, 0, 1, 1, 1)

        self.note_widget.raise_()
        self.project_info.raise_()
        self.name_selected_project.raise_()
        self.change_project_widget.raise_()
        self.scroll_projects = QScrollArea(self.projects_tab)
        self.scroll_projects.setObjectName(u"scroll_projects")
        self.scroll_projects.setGeometry(QRect(10, 60, 201, 501))
        self.scroll_projects.setFont(font)
        self.scroll_projects.setMouseTracking(True)
        self.scroll_projects.setTabletTracking(True)
        self.scroll_projects.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_projects.setWidgetResizable(True)
        self.scroll_projects.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(8, 0, 183, 499))
        self.scroll_projects.setWidget(self.scrollAreaWidgetContents_4)
        self.tabWidget.addTab(self.projects_tab, "")
        self.project_detail_widget.raise_()
        self.btns_create_filter.raise_()
        self.scroll_projects.raise_()
        self.game_tab = QWidget()
        self.game_tab.setObjectName(u"game_tab")
        self.horizontalLayout = QHBoxLayout(self.game_tab)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.label = QLabel(self.game_tab)
        self.label.setObjectName(u"label")
        font3 = QFont()
        font3.setFamilies([u"Arial"])
        font3.setPointSize(26)
        self.label.setFont(font3)

        self.horizontalLayout.addWidget(self.label)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.tabWidget.addTab(self.game_tab, "")
        main_window.setCentralWidget(self.centralwidget)

        self.retranslateUi(main_window)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"nfprogress", None))
        self.btn_create_project.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0437\u0434\u0430\u0442\u044c", None))
        self.filter_project_box.setItemText(0, QCoreApplication.translate("main_window", u"\u0410\u043a\u0442\u0438\u0432\u0435\u043d", None))
        self.filter_project_box.setItemText(1, QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432\u0435", None))
        self.filter_project_box.setItemText(2, QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d", None))

        self.project_info.setTitle(QCoreApplication.translate("main_window", u"\u0418\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f \u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.label_status.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u0430\u0442\u0443\u0441:", None))
        self.status.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_progress.setText(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.progress.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_goal.setText(QCoreApplication.translate("main_window", u"\u0426\u0435\u043b\u044c:", None))
        self.goal.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_total.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e:", None))
        self.total.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_today_added.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f:", None))
        self.added_today.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_need.setText(QCoreApplication.translate("main_window", u"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043d\u0430\u043f\u0438\u0441\u0430\u0442\u044c: ", None))
        self.need.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_deadline.setText(QCoreApplication.translate("main_window", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d:", None))
        self.deadline.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_streaks.setText(QCoreApplication.translate("main_window", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.streaks.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_streak_status.setText(QCoreApplication.translate("main_window", u"C\u0442\u0430\u0442\u0443\u0441 \u0441\u0442\u0440\u0438\u043a\u0430:", None))
        self.streak_status.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.label_max_streak.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.max_streak.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.last_note.setText(QCoreApplication.translate("main_window", u"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0437\u0430\u043f\u0438\u0441\u044c: ", None))
        self.l.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.name_selected_project.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.btn_complete_project.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c", None))
        self.btn_archived_project.setText(QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432", None))
        self.btn_delete_project.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.btn_change_project.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.label_3.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u043f\u0438\u0441\u0438 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.label_9.setText(QCoreApplication.translate("main_window", u"\u041d\u043e\u0432\u0430\u044f \u0437\u0430\u043f\u0438\u0441\u044c:", None))
        self.pb_save_flash_note.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.projects_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0435\u043a\u0442\u044b", None))
        self.label.setText(QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.game_tab), QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
    # retranslateUi

