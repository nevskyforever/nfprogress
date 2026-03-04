# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_windoweahHlY.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(727, 646)
        main_window.setMinimumSize(QSize(727, 646))
        main_window.setMaximumSize(QSize(727, 646))
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        main_window.setFont(font)
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(-1, 10, 731, 641))
        self.projects_tab = QWidget()
        self.projects_tab.setObjectName(u"projects_tab")
        self.btns_create_filter = QWidget(self.projects_tab)
        self.btns_create_filter.setObjectName(u"btns_create_filter")
        self.btns_create_filter.setGeometry(QRect(10, 40, 211, 45))
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
        self.project_detail_widget.setGeometry(QRect(220, 10, 501, 581))
        self.project_info = QGroupBox(self.project_detail_widget)
        self.project_info.setObjectName(u"project_info")
        self.project_info.setEnabled(True)
        self.project_info.setGeometry(QRect(10, 90, 461, 308))
        self.project_info.setFont(font)
        self.project_info.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.project_info.setFlat(False)
        self.gridLayout_2 = QGridLayout(self.project_info)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_status = QLabel(self.project_info)
        self.label_status.setObjectName(u"label_status")

        self.gridLayout_2.addWidget(self.label_status, 0, 0, 1, 1)

        self.status = QLabel(self.project_info)
        self.status.setObjectName(u"status")

        self.gridLayout_2.addWidget(self.status, 0, 1, 1, 1)

        self.label_progress = QLabel(self.project_info)
        self.label_progress.setObjectName(u"label_progress")

        self.gridLayout_2.addWidget(self.label_progress, 1, 0, 1, 1)

        self.progress = QLabel(self.project_info)
        self.progress.setObjectName(u"progress")

        self.gridLayout_2.addWidget(self.progress, 1, 1, 1, 1)

        self.label_goal = QLabel(self.project_info)
        self.label_goal.setObjectName(u"label_goal")

        self.gridLayout_2.addWidget(self.label_goal, 2, 0, 1, 1)

        self.goal = QLabel(self.project_info)
        self.goal.setObjectName(u"goal")

        self.gridLayout_2.addWidget(self.goal, 2, 1, 1, 1)

        self.label_total = QLabel(self.project_info)
        self.label_total.setObjectName(u"label_total")

        self.gridLayout_2.addWidget(self.label_total, 3, 0, 1, 1)

        self.total = QLabel(self.project_info)
        self.total.setObjectName(u"total")

        self.gridLayout_2.addWidget(self.total, 3, 1, 1, 1)

        self.label_today_added = QLabel(self.project_info)
        self.label_today_added.setObjectName(u"label_today_added")

        self.gridLayout_2.addWidget(self.label_today_added, 4, 0, 1, 1)

        self.added_today = QLabel(self.project_info)
        self.added_today.setObjectName(u"added_today")

        self.gridLayout_2.addWidget(self.added_today, 4, 1, 1, 1)

        self.label_need = QLabel(self.project_info)
        self.label_need.setObjectName(u"label_need")

        self.gridLayout_2.addWidget(self.label_need, 5, 0, 1, 1)

        self.need = QLabel(self.project_info)
        self.need.setObjectName(u"need")

        self.gridLayout_2.addWidget(self.need, 5, 1, 1, 1)

        self.label_deadline = QLabel(self.project_info)
        self.label_deadline.setObjectName(u"label_deadline")

        self.gridLayout_2.addWidget(self.label_deadline, 6, 0, 1, 1)

        self.deadline = QLabel(self.project_info)
        self.deadline.setObjectName(u"deadline")

        self.gridLayout_2.addWidget(self.deadline, 6, 1, 1, 1)

        self.label_streaks = QLabel(self.project_info)
        self.label_streaks.setObjectName(u"label_streaks")

        self.gridLayout_2.addWidget(self.label_streaks, 7, 0, 1, 1)

        self.streaks = QLabel(self.project_info)
        self.streaks.setObjectName(u"streaks")

        self.gridLayout_2.addWidget(self.streaks, 7, 1, 1, 1)

        self.label_streak_status = QLabel(self.project_info)
        self.label_streak_status.setObjectName(u"label_streak_status")

        self.gridLayout_2.addWidget(self.label_streak_status, 8, 0, 1, 1)

        self.streak_status = QLabel(self.project_info)
        self.streak_status.setObjectName(u"streak_status")

        self.gridLayout_2.addWidget(self.streak_status, 8, 1, 1, 1)

        self.label_max_streak = QLabel(self.project_info)
        self.label_max_streak.setObjectName(u"label_max_streak")

        self.gridLayout_2.addWidget(self.label_max_streak, 9, 0, 1, 1)

        self.max_streak = QLabel(self.project_info)
        self.max_streak.setObjectName(u"max_streak")

        self.gridLayout_2.addWidget(self.max_streak, 9, 1, 1, 1)

        self.last_note = QLabel(self.project_info)
        self.last_note.setObjectName(u"last_note")

        self.gridLayout_2.addWidget(self.last_note, 10, 0, 1, 1)

        self.l = QLabel(self.project_info)
        self.l.setObjectName(u"l")

        self.gridLayout_2.addWidget(self.l, 10, 1, 1, 1)

        self.name_selected_project = QLabel(self.project_detail_widget)
        self.name_selected_project.setObjectName(u"name_selected_project")
        self.name_selected_project.setGeometry(QRect(10, 0, 451, 31))
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        font1.setPointSize(20)
        self.name_selected_project.setFont(font1)
        self.name_selected_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.change_project_widget = QWidget(self.project_detail_widget)
        self.change_project_widget.setObjectName(u"change_project_widget")
        self.change_project_widget.setEnabled(False)
        self.change_project_widget.setGeometry(QRect(10, 30, 460, 45))
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

        self.note_widget = QWidget(self.project_detail_widget)
        self.note_widget.setObjectName(u"note_widget")
        self.note_widget.setGeometry(QRect(9, 359, 491, 241))
        self.label_3 = QLabel(self.note_widget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(-10, 80, 371, 20))
        font2 = QFont()
        font2.setFamilies([u"Arial"])
        font2.setPointSize(16)
        self.label_3.setFont(font2)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flash_note = QWidget(self.note_widget)
        self.flash_note.setObjectName(u"flash_note")
        self.flash_note.setGeometry(QRect(10, 40, 311, 45))
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

        self.note_list = QListWidget(self.note_widget)
        self.note_list.setObjectName(u"note_list")
        self.note_list.setGeometry(QRect(0, 100, 361, 121))
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
        self.delete_note = QPushButton(self.note_widget)
        self.delete_note.setObjectName(u"delete_note")
        self.delete_note.setGeometry(QRect(390, 150, 81, 32))
        self.note_widget.raise_()
        self.project_info.raise_()
        self.name_selected_project.raise_()
        self.change_project_widget.raise_()
        self.list_projects = QListWidget(self.projects_tab)
        self.list_projects.setObjectName(u"list_projects")
        self.list_projects.setGeometry(QRect(10, 90, 200, 501))
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
        self.tabWidget.addTab(self.projects_tab, "")
        self.project_detail_widget.raise_()
        self.btns_create_filter.raise_()
        self.list_projects.raise_()
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
        self.status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_progress.setText(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.progress.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_goal.setText(QCoreApplication.translate("main_window", u"\u0426\u0435\u043b\u044c:", None))
        self.goal.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_total.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e:", None))
        self.total.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_today_added.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f:", None))
        self.added_today.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_need.setText(QCoreApplication.translate("main_window", u"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043d\u0430\u043f\u0438\u0441\u0430\u0442\u044c: ", None))
        self.need.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_deadline.setText(QCoreApplication.translate("main_window", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d:", None))
        self.deadline.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_streaks.setText(QCoreApplication.translate("main_window", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.streaks.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_streak_status.setText(QCoreApplication.translate("main_window", u"C\u0442\u0430\u0442\u0443\u0441 \u0441\u0442\u0440\u0438\u043a\u0430:", None))
        self.streak_status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_max_streak.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.max_streak.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.last_note.setText(QCoreApplication.translate("main_window", u"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0437\u0430\u043f\u0438\u0441\u044c: ", None))
        self.l.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.name_selected_project.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.btn_change_project.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.btn_delete_project.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.btn_archived_project.setText(QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432", None))
        self.btn_complete_project.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c", None))
        self.label_3.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u043f\u0438\u0441\u0438 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.label_9.setText(QCoreApplication.translate("main_window", u"\u041d\u043e\u0432\u0430\u044f \u0437\u0430\u043f\u0438\u0441\u044c:", None))
        self.pb_save_flash_note.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", None))
        self.delete_note.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.projects_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0435\u043a\u0442\u044b", None))
        self.label.setText(QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c \u0432 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0435", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.game_tab), QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
    # retranslateUi

