# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_windowRTUzsF.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(992, 749)
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        main_window.setFont(font)
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_3 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.projects_tab = QWidget()
        self.projects_tab.setObjectName(u"projects_tab")
        self.gridLayout_3 = QGridLayout(self.projects_tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.btns_create_filter = QWidget(self.projects_tab)
        self.btns_create_filter.setObjectName(u"btns_create_filter")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btns_create_filter.sizePolicy().hasHeightForWidth())
        self.btns_create_filter.setSizePolicy(sizePolicy)
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


        self.gridLayout_3.addWidget(self.btns_create_filter, 1, 0, 1, 1)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_4, 1, 3, 1, 1)

        self.project_detail_widget = QWidget(self.projects_tab)
        self.project_detail_widget.setObjectName(u"project_detail_widget")
        self.gridLayout_4 = QGridLayout(self.project_detail_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.name_selected_project = QLabel(self.project_detail_widget)
        self.name_selected_project.setObjectName(u"name_selected_project")
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(20)
        self.name_selected_project.setFont(font1)
        self.name_selected_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_selected_project.setWordWrap(True)

        self.gridLayout_4.addWidget(self.name_selected_project, 0, 0, 1, 1)

        self.change_project_widget = QWidget(self.project_detail_widget)
        self.change_project_widget.setObjectName(u"change_project_widget")
        self.change_project_widget.setEnabled(False)
        self.change_project_widget.setFont(font)
        self.horizontalLayout_2 = QHBoxLayout(self.change_project_widget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_change_project = QPushButton(self.change_project_widget)
        self.btn_change_project.setObjectName(u"btn_change_project")
        self.btn_change_project.setEnabled(False)

        self.horizontalLayout_2.addWidget(self.btn_change_project)

        self.btn_delete_project = QPushButton(self.change_project_widget)
        self.btn_delete_project.setObjectName(u"btn_delete_project")
        self.btn_delete_project.setEnabled(False)

        self.horizontalLayout_2.addWidget(self.btn_delete_project)

        self.btn_archived_project = QPushButton(self.change_project_widget)
        self.btn_archived_project.setObjectName(u"btn_archived_project")
        self.btn_archived_project.setEnabled(False)
        self.btn_archived_project.setFont(font)

        self.horizontalLayout_2.addWidget(self.btn_archived_project)

        self.btn_complete_project = QPushButton(self.change_project_widget)
        self.btn_complete_project.setObjectName(u"btn_complete_project")
        self.btn_complete_project.setEnabled(False)
        self.btn_complete_project.setFont(font)

        self.horizontalLayout_2.addWidget(self.btn_complete_project)


        self.gridLayout_4.addWidget(self.change_project_widget, 2, 0, 1, 1)

        self.note_widget = QWidget(self.project_detail_widget)
        self.note_widget.setObjectName(u"note_widget")
        self.verticalLayout_2 = QVBoxLayout(self.note_widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_2 = QLabel(self.note_widget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_2)

        self.note_list = QListWidget(self.note_widget)
        self.note_list.setObjectName(u"note_list")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.note_list.sizePolicy().hasHeightForWidth())
        self.note_list.setSizePolicy(sizePolicy1)
        self.note_list.setStyleSheet(u"QListWidget#note_list {\n"
"    background-color: rgb(56, 56, 56);\n"
"    border: 1px solid #999;\n"
"    border-radius: 3px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QListWidget#note_list::item {\n"
"    padding: 4px;\n"
"    border-bottom: 1px solid #aaa;\n"
"}\n"
"\n"
"QListWidget#note_list::item:selected {\n"
"    background-color: #3daee9;\n"
"    color: white;\n"
"}\n"
"\n"
"QListWidget#note_list::item:hover {\n"
"    background-color: #d8d8d8;\n"
"}")

        self.verticalLayout_2.addWidget(self.note_list)

        self.flash_note = QWidget(self.note_widget)
        self.flash_note.setObjectName(u"flash_note")
        self.flash_note.setFont(font)
        self.gridLayout = QGridLayout(self.flash_note)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_9 = QLabel(self.flash_note)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 0, 0, 1, 1)

        self.delete_note = QPushButton(self.flash_note)
        self.delete_note.setObjectName(u"delete_note")

        self.gridLayout.addWidget(self.delete_note, 0, 3, 1, 1)

        self.pb_save_flash_note = QPushButton(self.flash_note)
        self.pb_save_flash_note.setObjectName(u"pb_save_flash_note")
        self.pb_save_flash_note.setEnabled(False)

        self.gridLayout.addWidget(self.pb_save_flash_note, 0, 2, 1, 1)

        self.new_symbols = QLineEdit(self.flash_note)
        self.new_symbols.setObjectName(u"new_symbols")

        self.gridLayout.addWidget(self.new_symbols, 0, 1, 1, 1)


        self.verticalLayout_2.addWidget(self.flash_note)


        self.gridLayout_4.addWidget(self.note_widget, 6, 0, 1, 1)

        self.project_info = QGroupBox(self.project_detail_widget)
        self.project_info.setObjectName(u"project_info")
        self.project_info.setEnabled(True)
        self.project_info.setFont(font)
        self.project_info.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.project_info.setFlat(False)
        self.gridLayout_2 = QGridLayout(self.project_info)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_today_added = QLabel(self.project_info)
        self.label_today_added.setObjectName(u"label_today_added")

        self.gridLayout_2.addWidget(self.label_today_added, 4, 0, 1, 1)

        self.label_progress = QLabel(self.project_info)
        self.label_progress.setObjectName(u"label_progress")

        self.gridLayout_2.addWidget(self.label_progress, 1, 0, 1, 1)

        self.label_status = QLabel(self.project_info)
        self.label_status.setObjectName(u"label_status")

        self.gridLayout_2.addWidget(self.label_status, 0, 0, 1, 1)

        self.label_need = QLabel(self.project_info)
        self.label_need.setObjectName(u"label_need")

        self.gridLayout_2.addWidget(self.label_need, 5, 0, 1, 1)

        self.last_note = QLabel(self.project_info)
        self.last_note.setObjectName(u"last_note")

        self.gridLayout_2.addWidget(self.last_note, 10, 0, 1, 1)

        self.streaks = QLabel(self.project_info)
        self.streaks.setObjectName(u"streaks")

        self.gridLayout_2.addWidget(self.streaks, 7, 1, 1, 1)

        self.max_streak = QLabel(self.project_info)
        self.max_streak.setObjectName(u"max_streak")

        self.gridLayout_2.addWidget(self.max_streak, 9, 1, 1, 1)

        self.label_max_streak = QLabel(self.project_info)
        self.label_max_streak.setObjectName(u"label_max_streak")

        self.gridLayout_2.addWidget(self.label_max_streak, 9, 0, 1, 1)

        self.status = QLabel(self.project_info)
        self.status.setObjectName(u"status")

        self.gridLayout_2.addWidget(self.status, 0, 1, 1, 1)

        self.added_today = QLabel(self.project_info)
        self.added_today.setObjectName(u"added_today")

        self.gridLayout_2.addWidget(self.added_today, 4, 1, 1, 1)

        self.l = QLabel(self.project_info)
        self.l.setObjectName(u"l")
        self.l.setWordWrap(True)

        self.gridLayout_2.addWidget(self.l, 10, 1, 1, 1)

        self.goal = QLabel(self.project_info)
        self.goal.setObjectName(u"goal")

        self.gridLayout_2.addWidget(self.goal, 2, 1, 1, 1)

        self.progress = QLabel(self.project_info)
        self.progress.setObjectName(u"progress")

        self.gridLayout_2.addWidget(self.progress, 1, 1, 1, 1)

        self.total = QLabel(self.project_info)
        self.total.setObjectName(u"total")

        self.gridLayout_2.addWidget(self.total, 3, 1, 1, 1)

        self.deadline = QLabel(self.project_info)
        self.deadline.setObjectName(u"deadline")

        self.gridLayout_2.addWidget(self.deadline, 6, 1, 1, 1)

        self.label_goal = QLabel(self.project_info)
        self.label_goal.setObjectName(u"label_goal")

        self.gridLayout_2.addWidget(self.label_goal, 2, 0, 1, 1)

        self.label_deadline = QLabel(self.project_info)
        self.label_deadline.setObjectName(u"label_deadline")

        self.gridLayout_2.addWidget(self.label_deadline, 6, 0, 1, 1)

        self.streak_status = QLabel(self.project_info)
        self.streak_status.setObjectName(u"streak_status")
        self.streak_status.setWordWrap(True)

        self.gridLayout_2.addWidget(self.streak_status, 8, 1, 1, 1)

        self.need = QLabel(self.project_info)
        self.need.setObjectName(u"need")

        self.gridLayout_2.addWidget(self.need, 5, 1, 1, 1)

        self.label_streak_status = QLabel(self.project_info)
        self.label_streak_status.setObjectName(u"label_streak_status")

        self.gridLayout_2.addWidget(self.label_streak_status, 8, 0, 1, 1)

        self.label_total = QLabel(self.project_info)
        self.label_total.setObjectName(u"label_total")

        self.gridLayout_2.addWidget(self.label_total, 3, 0, 1, 1)

        self.label_streaks = QLabel(self.project_info)
        self.label_streaks.setObjectName(u"label_streaks")

        self.gridLayout_2.addWidget(self.label_streaks, 7, 0, 1, 1)


        self.gridLayout_4.addWidget(self.project_info, 3, 0, 1, 1)


        self.gridLayout_3.addWidget(self.project_detail_widget, 1, 2, 3, 1)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_3, 3, 1, 1, 1)

        self.list_projects = QListWidget(self.projects_tab)
        self.list_projects.setObjectName(u"list_projects")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.list_projects.sizePolicy().hasHeightForWidth())
        self.list_projects.setSizePolicy(sizePolicy2)
        self.list_projects.setMouseTracking(True)
        self.list_projects.setStyleSheet(u"QListWidget#list_projects {\n"
"    background-color: rgb(56, 56, 56);\n"
"    border: 2px solid #999;\n"
"    border-radius: 5px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QListWidget#list_projects::item {\n"
"    padding: 5px;\n"
"    border-bottom: 1px solid #aaa;\n"
"}\n"
"\n"
"QListWidget#list_projects::item:selected {\n"
"    background-color: #3daee9;\n"
"    color: rgb(0, 28, 255);\n"
"}\n"
"\n"
"QListWidget#list_projects::item:hover {\n"
"    background-color: rgb(165, 165, 165);\n"
"}")
        self.list_projects.setSortingEnabled(False)

        self.gridLayout_3.addWidget(self.list_projects, 3, 0, 1, 1)

        self.global_streak_status = QLabel(self.projects_tab)
        self.global_streak_status.setObjectName(u"global_streak_status")
        self.global_streak_status.setWordWrap(False)

        self.gridLayout_3.addWidget(self.global_streak_status, 2, 0, 1, 1)

        self.tabWidget.addTab(self.projects_tab, "")
        self.project_detail_widget.raise_()
        self.btns_create_filter.raise_()
        self.list_projects.raise_()
        self.global_streak_status.raise_()
        self.game_tab = QWidget()
        self.game_tab.setObjectName(u"game_tab")
        self.gridLayout_5 = QGridLayout(self.game_tab)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.quests_tabs = QTabWidget(self.game_tab)
        self.quests_tabs.setObjectName(u"quests_tabs")
        sizePolicy.setHeightForWidth(self.quests_tabs.sizePolicy().hasHeightForWidth())
        self.quests_tabs.setSizePolicy(sizePolicy)
        self.available_quests_tab = QWidget()
        self.available_quests_tab.setObjectName(u"available_quests_tab")
        self.gridLayout_8 = QGridLayout(self.available_quests_tab)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.available_quests_list = QListWidget(self.available_quests_tab)
        self.available_quests_list.setObjectName(u"available_quests_list")
        sizePolicy.setHeightForWidth(self.available_quests_list.sizePolicy().hasHeightForWidth())
        self.available_quests_list.setSizePolicy(sizePolicy)
        self.available_quests_list.setMaximumSize(QSize(193, 16777215))

        self.gridLayout_8.addWidget(self.available_quests_list, 0, 0, 1, 1)

        self.about_selected_available_quest = QGroupBox(self.available_quests_tab)
        self.about_selected_available_quest.setObjectName(u"about_selected_available_quest")
        self.gridLayout_13 = QGridLayout(self.about_selected_available_quest)
        self.gridLayout_13.setObjectName(u"gridLayout_13")
        self.scrollArea_3 = QScrollArea(self.about_selected_available_quest)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 185, 169))
        self.gridLayout_14 = QGridLayout(self.scrollAreaWidgetContents_4)
        self.gridLayout_14.setObjectName(u"gridLayout_14")
        self.label_4 = QLabel(self.scrollAreaWidgetContents_4)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setWordWrap(True)

        self.gridLayout_14.addWidget(self.label_4, 0, 0, 1, 1)

        self.label_5 = QLabel(self.scrollAreaWidgetContents_4)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setWordWrap(True)

        self.gridLayout_14.addWidget(self.label_5, 1, 0, 1, 1)

        self.label_11 = QLabel(self.scrollAreaWidgetContents_4)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setWordWrap(True)

        self.gridLayout_14.addWidget(self.label_11, 2, 0, 1, 1)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_4)

        self.gridLayout_13.addWidget(self.scrollArea_3, 2, 1, 1, 1)

        self.button_for_start_selected_quest = QPushButton(self.about_selected_available_quest)
        self.button_for_start_selected_quest.setObjectName(u"button_for_start_selected_quest")

        self.gridLayout_13.addWidget(self.button_for_start_selected_quest, 3, 1, 1, 1)


        self.gridLayout_8.addWidget(self.about_selected_available_quest, 0, 1, 1, 1)

        self.quests_tabs.addTab(self.available_quests_tab, "")
        self.active_quests_tab = QWidget()
        self.active_quests_tab.setObjectName(u"active_quests_tab")
        self.gridLayout_9 = QGridLayout(self.active_quests_tab)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.active_quests_list = QListWidget(self.active_quests_tab)
        self.active_quests_list.setObjectName(u"active_quests_list")
        sizePolicy.setHeightForWidth(self.active_quests_list.sizePolicy().hasHeightForWidth())
        self.active_quests_list.setSizePolicy(sizePolicy)
        self.active_quests_list.setMaximumSize(QSize(193, 16777215))

        self.gridLayout_9.addWidget(self.active_quests_list, 0, 0, 1, 1)

        self.about_selected_active_quest = QGroupBox(self.active_quests_tab)
        self.about_selected_active_quest.setObjectName(u"about_selected_active_quest")
        self.verticalLayout = QVBoxLayout(self.about_selected_active_quest)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea_2 = QScrollArea(self.about_selected_active_quest)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 185, 169))
        self.gridLayout_17 = QGridLayout(self.scrollAreaWidgetContents_3)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.label_23 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setWordWrap(True)

        self.gridLayout_17.addWidget(self.label_23, 3, 0, 1, 1)

        self.label_20 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setWordWrap(True)

        self.gridLayout_17.addWidget(self.label_20, 0, 0, 1, 1)

        self.label_21 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setWordWrap(True)

        self.gridLayout_17.addWidget(self.label_21, 1, 0, 1, 1)

        self.label_24 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setWordWrap(True)

        self.gridLayout_17.addWidget(self.label_24, 4, 0, 1, 1)

        self.label_22 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setWordWrap(True)

        self.gridLayout_17.addWidget(self.label_22, 2, 0, 1, 1)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout.addWidget(self.scrollArea_2)

        self.button_for_stop_selected_quest = QPushButton(self.about_selected_active_quest)
        self.button_for_stop_selected_quest.setObjectName(u"button_for_stop_selected_quest")

        self.verticalLayout.addWidget(self.button_for_stop_selected_quest)


        self.gridLayout_9.addWidget(self.about_selected_active_quest, 0, 1, 1, 1)

        self.quests_tabs.addTab(self.active_quests_tab, "")
        self.completed_quests_tab = QWidget()
        self.completed_quests_tab.setObjectName(u"completed_quests_tab")
        self.gridLayout_10 = QGridLayout(self.completed_quests_tab)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.completed_quests_list = QListWidget(self.completed_quests_tab)
        self.completed_quests_list.setObjectName(u"completed_quests_list")
        sizePolicy.setHeightForWidth(self.completed_quests_list.sizePolicy().hasHeightForWidth())
        self.completed_quests_list.setSizePolicy(sizePolicy)
        self.completed_quests_list.setMaximumSize(QSize(193, 16777215))

        self.gridLayout_10.addWidget(self.completed_quests_list, 0, 0, 1, 1)

        self.about_selected_completed_quest = QGroupBox(self.completed_quests_tab)
        self.about_selected_completed_quest.setObjectName(u"about_selected_completed_quest")
        self.gridLayout_15 = QGridLayout(self.about_selected_completed_quest)
        self.gridLayout_15.setObjectName(u"gridLayout_15")
        self.scrollArea = QScrollArea(self.about_selected_completed_quest)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 185, 203))
        self.gridLayout_16 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_16.setObjectName(u"gridLayout_16")
        self.label_18 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setWordWrap(True)

        self.gridLayout_16.addWidget(self.label_18, 4, 0, 1, 1)

        self.label_17 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setWordWrap(True)

        self.gridLayout_16.addWidget(self.label_17, 2, 0, 1, 1)

        self.label_15 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setWordWrap(True)

        self.gridLayout_16.addWidget(self.label_15, 1, 0, 1, 1)

        self.label_16 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setWordWrap(True)

        self.gridLayout_16.addWidget(self.label_16, 0, 0, 1, 1)

        self.label_19 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setWordWrap(True)

        self.gridLayout_16.addWidget(self.label_19, 3, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_15.addWidget(self.scrollArea, 0, 1, 1, 1)


        self.gridLayout_10.addWidget(self.about_selected_completed_quest, 0, 1, 1, 1)

        self.quests_tabs.addTab(self.completed_quests_tab, "")

        self.gridLayout_5.addWidget(self.quests_tabs, 4, 0, 1, 1)

        self.inventory_frame = QFrame(self.game_tab)
        self.inventory_frame.setObjectName(u"inventory_frame")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.inventory_frame.sizePolicy().hasHeightForWidth())
        self.inventory_frame.setSizePolicy(sizePolicy3)
        self.inventory_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.inventory_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.inventory_frame)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.inventory_list = QListWidget(self.inventory_frame)
        self.inventory_list.setObjectName(u"inventory_list")
        sizePolicy.setHeightForWidth(self.inventory_list.sizePolicy().hasHeightForWidth())
        self.inventory_list.setSizePolicy(sizePolicy)
        self.inventory_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout_5.addWidget(self.inventory_list)

        self.inventory_scroll_area = QGroupBox(self.inventory_frame)
        self.inventory_scroll_area.setObjectName(u"inventory_scroll_area")
        self.gridLayout_12 = QGridLayout(self.inventory_scroll_area)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.value_for_use_selected_item = QSpinBox(self.inventory_scroll_area)
        self.value_for_use_selected_item.setObjectName(u"value_for_use_selected_item")
        self.value_for_use_selected_item.setMinimum(1)
        self.value_for_use_selected_item.setSingleStep(1)
        self.value_for_use_selected_item.setValue(1)

        self.gridLayout_12.addWidget(self.value_for_use_selected_item, 1, 1, 1, 1)

        self.label_13 = QLabel(self.inventory_scroll_area)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_13, 1, 0, 1, 1)

        self.about_selected_inventory_item = QScrollArea(self.inventory_scroll_area)
        self.about_selected_inventory_item.setObjectName(u"about_selected_inventory_item")
        self.about_selected_inventory_item.setWidgetResizable(True)
        self.scrollAreaWidgetContents_6 = QWidget()
        self.scrollAreaWidgetContents_6.setObjectName(u"scrollAreaWidgetContents_6")
        self.scrollAreaWidgetContents_6.setGeometry(QRect(0, 0, 189, 119))
        self.gridLayout_19 = QGridLayout(self.scrollAreaWidgetContents_6)
        self.gridLayout_19.setObjectName(u"gridLayout_19")
        self.name_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.name_selected_item.setObjectName(u"name_selected_item")
        self.name_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.name_selected_item, 0, 0, 1, 1)

        self.level_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.level_selected_item.setObjectName(u"level_selected_item")
        self.level_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.level_selected_item, 2, 0, 1, 1)

        self.effect_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.effect_selected_item.setObjectName(u"effect_selected_item")
        self.effect_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.effect_selected_item, 3, 0, 1, 1)

        self.description_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.description_selected_item.setObjectName(u"description_selected_item")
        self.description_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.description_selected_item, 1, 0, 1, 1)

        self.about_selected_inventory_item.setWidget(self.scrollAreaWidgetContents_6)

        self.gridLayout_12.addWidget(self.about_selected_inventory_item, 0, 0, 1, 2)

        self.button_for_selected_item = QPushButton(self.inventory_scroll_area)
        self.button_for_selected_item.setObjectName(u"button_for_selected_item")

        self.gridLayout_12.addWidget(self.button_for_selected_item, 2, 0, 1, 2)


        self.horizontalLayout_5.addWidget(self.inventory_scroll_area)


        self.gridLayout_5.addWidget(self.inventory_frame, 2, 1, 1, 1)

        self.label_8 = QLabel(self.game_tab)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMaximumSize(QSize(16777215, 18))
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.label_8, 1, 0, 1, 1)

        self.frame_5 = QFrame(self.game_tab)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(43)
        sizePolicy4.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy4)
        self.frame_5.setMinimumSize(QSize(0, 55))
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_6 = QGridLayout(self.frame_5)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gamer_health = QLabel(self.frame_5)
        self.gamer_health.setObjectName(u"gamer_health")
        self.gamer_health.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_health, 0, 3, 1, 1)

        self.label = QLabel(self.frame_5)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label, 0, 0, 1, 1)

        self.gamer_exp = QLabel(self.frame_5)
        self.gamer_exp.setObjectName(u"gamer_exp")
        self.gamer_exp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_exp, 0, 2, 1, 1)

        self.exp_progressbar = QProgressBar(self.frame_5)
        self.exp_progressbar.setObjectName(u"exp_progressbar")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.exp_progressbar.sizePolicy().hasHeightForWidth())
        self.exp_progressbar.setSizePolicy(sizePolicy5)
        self.exp_progressbar.setValue(24)

        self.gridLayout_6.addWidget(self.exp_progressbar, 1, 2, 1, 1)

        self.gamer_health_progressbar = QProgressBar(self.frame_5)
        self.gamer_health_progressbar.setObjectName(u"gamer_health_progressbar")
        sizePolicy5.setHeightForWidth(self.gamer_health_progressbar.sizePolicy().hasHeightForWidth())
        self.gamer_health_progressbar.setSizePolicy(sizePolicy5)
        self.gamer_health_progressbar.setValue(24)

        self.gridLayout_6.addWidget(self.gamer_health_progressbar, 1, 3, 1, 1)

        self.label_3 = QLabel(self.frame_5)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label_3, 0, 1, 1, 1)

        self.gamer_label = QLabel(self.frame_5)
        self.gamer_label.setObjectName(u"gamer_label")
        self.gamer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_label, 1, 0, 1, 1)

        self.gamer_coins = QLabel(self.frame_5)
        self.gamer_coins.setObjectName(u"gamer_coins")
        self.gamer_coins.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_coins, 1, 1, 1, 1)


        self.gridLayout_5.addWidget(self.frame_5, 0, 0, 1, 2)

        self.label_10 = QLabel(self.game_tab)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.label_10, 1, 1, 1, 1)

        self.parameters_tabs = QTabWidget(self.game_tab)
        self.parameters_tabs.setObjectName(u"parameters_tabs")
        sizePolicy.setHeightForWidth(self.parameters_tabs.sizePolicy().hasHeightForWidth())
        self.parameters_tabs.setSizePolicy(sizePolicy)
        self.bufs_tab = QWidget()
        self.bufs_tab.setObjectName(u"bufs_tab")
        self.horizontalLayout_7 = QHBoxLayout(self.bufs_tab)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.buf_list = QListWidget(self.bufs_tab)
        self.buf_list.setObjectName(u"buf_list")
        sizePolicy.setHeightForWidth(self.buf_list.sizePolicy().hasHeightForWidth())
        self.buf_list.setSizePolicy(sizePolicy)
        self.buf_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout_7.addWidget(self.buf_list)

        self.about_selected_buf = QGroupBox(self.bufs_tab)
        self.about_selected_buf.setObjectName(u"about_selected_buf")
        self.gridLayout_22 = QGridLayout(self.about_selected_buf)
        self.gridLayout_22.setObjectName(u"gridLayout_22")
        self.scrollArea_7 = QScrollArea(self.about_selected_buf)
        self.scrollArea_7.setObjectName(u"scrollArea_7")
        self.scrollArea_7.setWidgetResizable(True)
        self.scrollAreaWidgetContents_8 = QWidget()
        self.scrollAreaWidgetContents_8.setObjectName(u"scrollAreaWidgetContents_8")
        self.scrollAreaWidgetContents_8.setGeometry(QRect(0, 0, 185, 163))
        self.gridLayout_23 = QGridLayout(self.scrollAreaWidgetContents_8)
        self.gridLayout_23.setObjectName(u"gridLayout_23")
        self.label_37 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_37.setObjectName(u"label_37")
        self.label_37.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_37, 4, 0, 1, 1)

        self.label_38 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_38.setObjectName(u"label_38")
        self.label_38.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_38, 2, 0, 1, 1)

        self.label_39 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_39.setObjectName(u"label_39")
        self.label_39.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_39, 1, 0, 1, 1)

        self.label_40 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_40.setObjectName(u"label_40")
        self.label_40.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_40, 0, 0, 1, 1)

        self.label_41 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_41.setObjectName(u"label_41")
        self.label_41.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_41, 3, 0, 1, 1)

        self.scrollArea_7.setWidget(self.scrollAreaWidgetContents_8)

        self.gridLayout_22.addWidget(self.scrollArea_7, 0, 0, 1, 1)


        self.horizontalLayout_7.addWidget(self.about_selected_buf)

        self.parameters_tabs.addTab(self.bufs_tab, "")
        self.defufs_tab = QWidget()
        self.defufs_tab.setObjectName(u"defufs_tab")
        self.horizontalLayout_8 = QHBoxLayout(self.defufs_tab)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.debuf_list = QListWidget(self.defufs_tab)
        self.debuf_list.setObjectName(u"debuf_list")
        sizePolicy.setHeightForWidth(self.debuf_list.sizePolicy().hasHeightForWidth())
        self.debuf_list.setSizePolicy(sizePolicy)
        self.debuf_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout_8.addWidget(self.debuf_list)

        self.about_selected_debuf = QGroupBox(self.defufs_tab)
        self.about_selected_debuf.setObjectName(u"about_selected_debuf")
        self.gridLayout_24 = QGridLayout(self.about_selected_debuf)
        self.gridLayout_24.setObjectName(u"gridLayout_24")
        self.scrol_area = QScrollArea(self.about_selected_debuf)
        self.scrol_area.setObjectName(u"scrol_area")
        self.scrol_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents_9 = QWidget()
        self.scrollAreaWidgetContents_9.setObjectName(u"scrollAreaWidgetContents_9")
        self.scrollAreaWidgetContents_9.setGeometry(QRect(0, 0, 185, 163))
        self.gridLayout_25 = QGridLayout(self.scrollAreaWidgetContents_9)
        self.gridLayout_25.setObjectName(u"gridLayout_25")
        self.label_42 = QLabel(self.scrollAreaWidgetContents_9)
        self.label_42.setObjectName(u"label_42")
        self.label_42.setWordWrap(True)

        self.gridLayout_25.addWidget(self.label_42, 4, 0, 1, 1)

        self.label_43 = QLabel(self.scrollAreaWidgetContents_9)
        self.label_43.setObjectName(u"label_43")
        self.label_43.setWordWrap(True)

        self.gridLayout_25.addWidget(self.label_43, 2, 0, 1, 1)

        self.label_44 = QLabel(self.scrollAreaWidgetContents_9)
        self.label_44.setObjectName(u"label_44")
        self.label_44.setWordWrap(True)

        self.gridLayout_25.addWidget(self.label_44, 1, 0, 1, 1)

        self.label_45 = QLabel(self.scrollAreaWidgetContents_9)
        self.label_45.setObjectName(u"label_45")
        self.label_45.setWordWrap(True)

        self.gridLayout_25.addWidget(self.label_45, 0, 0, 1, 1)

        self.label_46 = QLabel(self.scrollAreaWidgetContents_9)
        self.label_46.setObjectName(u"label_46")
        self.label_46.setWordWrap(True)

        self.gridLayout_25.addWidget(self.label_46, 3, 0, 1, 1)

        self.scrol_area.setWidget(self.scrollAreaWidgetContents_9)

        self.gridLayout_24.addWidget(self.scrol_area, 0, 0, 1, 1)


        self.horizontalLayout_8.addWidget(self.about_selected_debuf)

        self.parameters_tabs.addTab(self.defufs_tab, "")

        self.gridLayout_5.addWidget(self.parameters_tabs, 2, 0, 1, 1)

        self.label_6 = QLabel(self.game_tab)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setMaximumSize(QSize(16777215, 18))
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.label_6, 3, 0, 1, 1)

        self.label_7 = QLabel(self.game_tab)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.label_7, 3, 1, 1, 1)

        self.game_shop_tabs = QTabWidget(self.game_tab)
        self.game_shop_tabs.setObjectName(u"game_shop_tabs")
        sizePolicy.setHeightForWidth(self.game_shop_tabs.sizePolicy().hasHeightForWidth())
        self.game_shop_tabs.setSizePolicy(sizePolicy)
        self.items_shop_tab = QWidget()
        self.items_shop_tab.setObjectName(u"items_shop_tab")
        self.horizontalLayout_6 = QHBoxLayout(self.items_shop_tab)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.item_shop_list = QListWidget(self.items_shop_tab)
        self.item_shop_list.setObjectName(u"item_shop_list")
        sizePolicy.setHeightForWidth(self.item_shop_list.sizePolicy().hasHeightForWidth())
        self.item_shop_list.setSizePolicy(sizePolicy)
        self.item_shop_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout_6.addWidget(self.item_shop_list)

        self.selected_goods_item_infobox = QGroupBox(self.items_shop_tab)
        self.selected_goods_item_infobox.setObjectName(u"selected_goods_item_infobox")
        self.gridLayout_20 = QGridLayout(self.selected_goods_item_infobox)
        self.gridLayout_20.setObjectName(u"gridLayout_20")
        self.value_for_buy_selected_item = QSpinBox(self.selected_goods_item_infobox)
        self.value_for_buy_selected_item.setObjectName(u"value_for_buy_selected_item")
        self.value_for_buy_selected_item.setMinimum(1)
        self.value_for_buy_selected_item.setValue(1)

        self.gridLayout_20.addWidget(self.value_for_buy_selected_item, 1, 1, 1, 1)

        self.label_14 = QLabel(self.selected_goods_item_infobox)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_20.addWidget(self.label_14, 1, 0, 1, 1)

        self.about_selected_goods = QScrollArea(self.selected_goods_item_infobox)
        self.about_selected_goods.setObjectName(u"about_selected_goods")
        self.about_selected_goods.setWidgetResizable(True)
        self.scrollAreaWidgetContents_7 = QWidget()
        self.scrollAreaWidgetContents_7.setObjectName(u"scrollAreaWidgetContents_7")
        self.scrollAreaWidgetContents_7.setGeometry(QRect(0, 0, 185, 138))
        self.gridLayout_21 = QGridLayout(self.scrollAreaWidgetContents_7)
        self.gridLayout_21.setObjectName(u"gridLayout_21")
        self.label_35 = QLabel(self.scrollAreaWidgetContents_7)
        self.label_35.setObjectName(u"label_35")

        self.gridLayout_21.addWidget(self.label_35, 4, 0, 1, 1)

        self.label_34 = QLabel(self.scrollAreaWidgetContents_7)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setWordWrap(True)

        self.gridLayout_21.addWidget(self.label_34, 3, 0, 1, 1)

        self.label_33 = QLabel(self.scrollAreaWidgetContents_7)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setWordWrap(True)

        self.gridLayout_21.addWidget(self.label_33, 0, 0, 1, 1)

        self.label_36 = QLabel(self.scrollAreaWidgetContents_7)
        self.label_36.setObjectName(u"label_36")
        self.label_36.setWordWrap(True)

        self.gridLayout_21.addWidget(self.label_36, 2, 0, 1, 1)

        self.label_47 = QLabel(self.scrollAreaWidgetContents_7)
        self.label_47.setObjectName(u"label_47")
        self.label_47.setScaledContents(False)
        self.label_47.setWordWrap(True)

        self.gridLayout_21.addWidget(self.label_47, 1, 0, 1, 1)

        self.about_selected_goods.setWidget(self.scrollAreaWidgetContents_7)

        self.gridLayout_20.addWidget(self.about_selected_goods, 0, 0, 1, 2)

        self.button_for_buy_selected_item = QPushButton(self.selected_goods_item_infobox)
        self.button_for_buy_selected_item.setObjectName(u"button_for_buy_selected_item")

        self.gridLayout_20.addWidget(self.button_for_buy_selected_item, 2, 0, 1, 2)


        self.horizontalLayout_6.addWidget(self.selected_goods_item_infobox)

        self.game_shop_tabs.addTab(self.items_shop_tab, "")
        self.potions_shop_tab = QWidget()
        self.potions_shop_tab.setObjectName(u"potions_shop_tab")
        self.horizontalLayout = QHBoxLayout(self.potions_shop_tab)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.potion_shop_list = QListWidget(self.potions_shop_tab)
        self.potion_shop_list.setObjectName(u"potion_shop_list")
        sizePolicy.setHeightForWidth(self.potion_shop_list.sizePolicy().hasHeightForWidth())
        self.potion_shop_list.setSizePolicy(sizePolicy)
        self.potion_shop_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout.addWidget(self.potion_shop_list)

        self.selected_goods_potion_infobox = QGroupBox(self.potions_shop_tab)
        self.selected_goods_potion_infobox.setObjectName(u"selected_goods_potion_infobox")
        self.gridLayout_11 = QGridLayout(self.selected_goods_potion_infobox)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.value_for_buy_selected_potion = QSpinBox(self.selected_goods_potion_infobox)
        self.value_for_buy_selected_potion.setObjectName(u"value_for_buy_selected_potion")
        self.value_for_buy_selected_potion.setMinimum(1)
        self.value_for_buy_selected_potion.setValue(1)

        self.gridLayout_11.addWidget(self.value_for_buy_selected_potion, 1, 1, 1, 1)

        self.label_12 = QLabel(self.selected_goods_potion_infobox)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_11.addWidget(self.label_12, 1, 0, 1, 1)

        self.scrollArea_4 = QScrollArea(self.selected_goods_potion_infobox)
        self.scrollArea_4.setObjectName(u"scrollArea_4")
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName(u"scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 185, 138))
        self.gridLayout_18 = QGridLayout(self.scrollAreaWidgetContents_5)
        self.gridLayout_18.setObjectName(u"gridLayout_18")
        self.label_26 = QLabel(self.scrollAreaWidgetContents_5)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setWordWrap(True)

        self.gridLayout_18.addWidget(self.label_26, 0, 0, 1, 1)

        self.label_29 = QLabel(self.scrollAreaWidgetContents_5)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setWordWrap(True)

        self.gridLayout_18.addWidget(self.label_29, 2, 0, 1, 1)

        self.label_25 = QLabel(self.scrollAreaWidgetContents_5)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setWordWrap(True)

        self.gridLayout_18.addWidget(self.label_25, 3, 0, 1, 1)

        self.label_27 = QLabel(self.scrollAreaWidgetContents_5)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setWordWrap(True)

        self.gridLayout_18.addWidget(self.label_27, 1, 0, 1, 1)

        self.scrollArea_4.setWidget(self.scrollAreaWidgetContents_5)

        self.gridLayout_11.addWidget(self.scrollArea_4, 0, 0, 1, 2)

        self.button_for_buy_selected_potion = QPushButton(self.selected_goods_potion_infobox)
        self.button_for_buy_selected_potion.setObjectName(u"button_for_buy_selected_potion")

        self.gridLayout_11.addWidget(self.button_for_buy_selected_potion, 2, 0, 1, 2)


        self.horizontalLayout.addWidget(self.selected_goods_potion_infobox)

        self.game_shop_tabs.addTab(self.potions_shop_tab, "")

        self.gridLayout_5.addWidget(self.game_shop_tabs, 4, 1, 1, 1)

        self.tabWidget.addTab(self.game_tab, "")

        self.horizontalLayout_3.addWidget(self.tabWidget)

        main_window.setCentralWidget(self.centralwidget)

        self.retranslateUi(main_window)

        self.tabWidget.setCurrentIndex(0)
        self.quests_tabs.setCurrentIndex(2)
        self.parameters_tabs.setCurrentIndex(1)
        self.game_shop_tabs.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"nfprogress", None))
        self.btn_create_project.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0437\u0434\u0430\u0442\u044c", None))
        self.filter_project_box.setItemText(0, QCoreApplication.translate("main_window", u"\u0410\u043a\u0442\u0438\u0432\u0435\u043d", None))
        self.filter_project_box.setItemText(1, QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432\u0435", None))
        self.filter_project_box.setItemText(2, QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d", None))

        self.name_selected_project.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.btn_change_project.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.btn_delete_project.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.btn_archived_project.setText(QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432", None))
        self.btn_complete_project.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c", None))
        self.label_2.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u043f\u0438\u0441\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
        self.label_9.setText(QCoreApplication.translate("main_window", u"\u041d\u043e\u0432\u0430\u044f \u0437\u0430\u043f\u0438\u0441\u044c:", None))
        self.delete_note.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.pb_save_flash_note.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", None))
        self.project_info.setTitle(QCoreApplication.translate("main_window", u"\u0418\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f \u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.label_today_added.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f:", None))
        self.label_progress.setText(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.label_status.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u0430\u0442\u0443\u0441:", None))
        self.label_need.setText(QCoreApplication.translate("main_window", u"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043d\u0430\u043f\u0438\u0441\u0430\u0442\u044c: ", None))
        self.last_note.setText(QCoreApplication.translate("main_window", u"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0437\u0430\u043f\u0438\u0441\u044c: ", None))
        self.streaks.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.max_streak.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_max_streak.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.added_today.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.l.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.goal.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.progress.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.total.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.deadline.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_goal.setText(QCoreApplication.translate("main_window", u"\u0426\u0435\u043b\u044c:", None))
        self.label_deadline.setText(QCoreApplication.translate("main_window", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d:", None))
        self.streak_status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.need.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_streak_status.setText(QCoreApplication.translate("main_window", u"C\u0442\u0430\u0442\u0443\u0441 \u0441\u0442\u0440\u0438\u043a\u0430:", None))
        self.label_total.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e:", None))
        self.label_streaks.setText(QCoreApplication.translate("main_window", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.global_streak_status.setText(QCoreApplication.translate("main_window", u"\u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.projects_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0435\u043a\u0442\u044b", None))
        self.about_selected_available_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.label_4.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_5.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_11.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.button_for_start_selected_quest.setText(QCoreApplication.translate("main_window", u"\u0412\u0437\u044f\u0442\u044c \u043a\u0432\u0435\u0441\u0442", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.available_quests_tab), QCoreApplication.translate("main_window", u"\u0414\u043e\u0441\u0442\u0443\u043f\u044b\u043d\u0435", None))
        self.about_selected_active_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.label_23.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.label_20.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_21.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_24.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.label_22.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.button_for_stop_selected_quest.setText(QCoreApplication.translate("main_window", u"\u041e\u0442\u043a\u0430\u0437\u0430\u0442\u044c\u0441\u044f \u043e\u0442 \u043a\u0432\u0435\u0441\u0442\u0430", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.active_quests_tab), QCoreApplication.translate("main_window", u"\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435", None))
        self.about_selected_completed_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.label_18.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.label_17.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.label_15.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_16.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_19.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.completed_quests_tab), QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043d\u044b\u0435", None))
        self.inventory_scroll_area.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.label_13.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.name_selected_item.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.level_selected_item.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.effect_selected_item.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.description_selected_item.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.button_for_selected_item.setText(QCoreApplication.translate("main_window", u"\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c", None))
        self.label_8.setText(QCoreApplication.translate("main_window", u"\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430", None))
        self.gamer_health.setText(QCoreApplication.translate("main_window", u"\u0417\u0434\u043e\u0440\u043e\u0432\u044c\u0435 100/100", None))
        self.label.setText(QCoreApplication.translate("main_window", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c", None))
        self.gamer_exp.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u044b\u0442: 0/100", None))
        self.label_3.setText(QCoreApplication.translate("main_window", u"\u041c\u043e\u043d\u0435\u0442\u044b", None))
        self.gamer_label.setText(QCoreApplication.translate("main_window", u"1", None))
        self.gamer_coins.setText(QCoreApplication.translate("main_window", u"0", None))
        self.label_10.setText(QCoreApplication.translate("main_window", u"\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u044c", None))
        self.about_selected_buf.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0431\u0430\u0444\u0435", None))
        self.label_37.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.label_38.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442", None))
        self.label_39.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_40.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_41.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.parameters_tabs.setTabText(self.parameters_tabs.indexOf(self.bufs_tab), QCoreApplication.translate("main_window", u"\u0411\u0430\u0444\u044b", None))
        self.about_selected_debuf.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0431\u0430\u0444\u0435", None))
        self.label_42.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.label_43.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442", None))
        self.label_44.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_45.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_46.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.parameters_tabs.setTabText(self.parameters_tabs.indexOf(self.defufs_tab), QCoreApplication.translate("main_window", u"\u0414\u0435\u0431\u0430\u0444\u044b", None))
        self.label_6.setText(QCoreApplication.translate("main_window", u"\u041a\u0432\u0435\u0441\u0442\u044b", None))
        self.label_7.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u0433\u0430\u0437\u0438\u043d", None))
        self.selected_goods_item_infobox.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.label_14.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.label_35.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.label_34.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.label_33.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_36.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.label_47.setText(QCoreApplication.translate("main_window", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c", None))
        self.button_for_buy_selected_item.setText(QCoreApplication.translate("main_window", u"\u041a\u0443\u043f\u0438\u0442\u044c", None))
        self.game_shop_tabs.setTabText(self.game_shop_tabs.indexOf(self.items_shop_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u0435\u0434\u043c\u0435\u0442\u044b", None))
        self.selected_goods_potion_infobox.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.label_12.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.label_26.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.label_29.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.label_25.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.label_27.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.button_for_buy_selected_potion.setText(QCoreApplication.translate("main_window", u"\u041a\u0443\u043f\u0438\u0442\u044c", None))
        self.game_shop_tabs.setTabText(self.game_shop_tabs.indexOf(self.potions_shop_tab), QCoreApplication.translate("main_window", u"\u0417\u0435\u043b\u044c\u044f", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.game_tab), QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
    # retranslateUi

