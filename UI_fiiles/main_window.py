# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_windowgsuEJf.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMenuBar, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(1380, 765)
        font = QFont()
        font.setFamilies([u"Arial"])
        font.setPointSize(14)
        main_window.setFont(font)
        main_window.setStyleSheet(u"QScrollArea {\n"
"    border: none;\n"
"}")
        self.synch_action = QAction(main_window)
        self.synch_action.setObjectName(u"synch_action")
        self.del_synch_action = QAction(main_window)
        self.del_synch_action.setObjectName(u"del_synch_action")
        self.delete_project_action = QAction(main_window)
        self.delete_project_action.setObjectName(u"delete_project_action")
        self.change_project_action = QAction(main_window)
        self.change_project_action.setObjectName(u"change_project_action")
        self.create_project_action = QAction(main_window)
        self.create_project_action.setObjectName(u"create_project_action")
        self.project_stats_action = QAction(main_window)
        self.project_stats_action.setObjectName(u"project_stats_action")
        self.archive_project_action = QAction(main_window)
        self.archive_project_action.setObjectName(u"archive_project_action")
        self.complete_project_action = QAction(main_window)
        self.complete_project_action.setObjectName(u"complete_project_action")
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_2 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        font1 = QFont()
        font1.setFamilies([u"Arial"])
        self.tabWidget.setFont(font1)
        self.tabWidget.setTabShape(QTabWidget.TabShape.Rounded)
        self.tabWidget.setUsesScrollButtons(False)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setTabBarAutoHide(False)
        self.projects_tab = QWidget()
        self.projects_tab.setObjectName(u"projects_tab")
        self.gridLayout_3 = QGridLayout(self.projects_tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.list_projects = QListWidget(self.projects_tab)
        self.list_projects.setObjectName(u"list_projects")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.list_projects.sizePolicy().hasHeightForWidth())
        self.list_projects.setSizePolicy(sizePolicy)
        font2 = QFont()
        font2.setFamilies([u"Arial"])
        font2.setPointSize(12)
        self.list_projects.setFont(font2)
        self.list_projects.setMouseTracking(True)
        self.list_projects.setStyleSheet(u"")
        self.list_projects.setSortingEnabled(False)

        self.gridLayout_3.addWidget(self.list_projects, 5, 0, 1, 1)

        self.btns_create_filter = QWidget(self.projects_tab)
        self.btns_create_filter.setObjectName(u"btns_create_filter")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.btns_create_filter.sizePolicy().hasHeightForWidth())
        self.btns_create_filter.setSizePolicy(sizePolicy1)
        self.btns_create_filter.setFont(font)
        self.gridLayout_26 = QGridLayout(self.btns_create_filter)
        self.gridLayout_26.setObjectName(u"gridLayout_26")
        self.sort_project_box = QComboBox(self.btns_create_filter)
        self.sort_project_box.addItem("")
        self.sort_project_box.addItem("")
        self.sort_project_box.addItem("")
        self.sort_project_box.setObjectName(u"sort_project_box")
        self.sort_project_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.gridLayout_26.addWidget(self.sort_project_box, 2, 1, 1, 1)

        self.label_5 = QLabel(self.btns_create_filter)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_26.addWidget(self.label_5, 1, 1, 1, 1)

        self.label_4 = QLabel(self.btns_create_filter)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_26.addWidget(self.label_4, 1, 0, 1, 1)

        self.filter_project_box = QComboBox(self.btns_create_filter)
        self.filter_project_box.addItem("")
        self.filter_project_box.addItem("")
        self.filter_project_box.addItem("")
        self.filter_project_box.setObjectName(u"filter_project_box")

        self.gridLayout_26.addWidget(self.filter_project_box, 2, 0, 1, 1)

        self.btn_create_project = QPushButton(self.btns_create_filter)
        self.btn_create_project.setObjectName(u"btn_create_project")
        sizePolicy1.setHeightForWidth(self.btn_create_project.sizePolicy().hasHeightForWidth())
        self.btn_create_project.setSizePolicy(sizePolicy1)
        self.btn_create_project.setFont(font)

        self.gridLayout_26.addWidget(self.btn_create_project, 3, 0, 1, 1)


        self.gridLayout_3.addWidget(self.btns_create_filter, 1, 0, 1, 1)

        self.project_detail_widget = QWidget(self.projects_tab)
        self.project_detail_widget.setObjectName(u"project_detail_widget")
        self.gridLayout_4 = QGridLayout(self.project_detail_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.name_selected_project = QLabel(self.project_detail_widget)
        self.name_selected_project.setObjectName(u"name_selected_project")
        font3 = QFont()
        font3.setFamilies([u"Arial"])
        font3.setPointSize(20)
        self.name_selected_project.setFont(font3)
        self.name_selected_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_selected_project.setWordWrap(True)

        self.gridLayout_4.addWidget(self.name_selected_project, 0, 0, 1, 1)

        self.change_project_widget = QWidget(self.project_detail_widget)
        self.change_project_widget.setObjectName(u"change_project_widget")
        self.change_project_widget.setEnabled(False)
        self.change_project_widget.setFont(font)
        self.gridLayout_29 = QGridLayout(self.change_project_widget)
        self.gridLayout_29.setObjectName(u"gridLayout_29")
        self.btn_change_project = QPushButton(self.change_project_widget)
        self.btn_change_project.setObjectName(u"btn_change_project")
        self.btn_change_project.setEnabled(False)

        self.gridLayout_29.addWidget(self.btn_change_project, 0, 1, 1, 1)

        self.btn_delete_project = QPushButton(self.change_project_widget)
        self.btn_delete_project.setObjectName(u"btn_delete_project")
        self.btn_delete_project.setEnabled(False)

        self.gridLayout_29.addWidget(self.btn_delete_project, 0, 2, 1, 1)

        self.btn_synch_project = QPushButton(self.change_project_widget)
        self.btn_synch_project.setObjectName(u"btn_synch_project")

        self.gridLayout_29.addWidget(self.btn_synch_project, 0, 0, 1, 1)

        self.btn_archived_project = QPushButton(self.change_project_widget)
        self.btn_archived_project.setObjectName(u"btn_archived_project")
        self.btn_archived_project.setEnabled(False)
        self.btn_archived_project.setFont(font)

        self.gridLayout_29.addWidget(self.btn_archived_project, 0, 3, 1, 1)

        self.btn_complete_project = QPushButton(self.change_project_widget)
        self.btn_complete_project.setObjectName(u"btn_complete_project")
        self.btn_complete_project.setEnabled(False)
        self.btn_complete_project.setFont(font)

        self.gridLayout_29.addWidget(self.btn_complete_project, 0, 4, 1, 1)

        self.synch_status = QLabel(self.change_project_widget)
        self.synch_status.setObjectName(u"synch_status")
        self.synch_status.setWordWrap(False)

        self.gridLayout_29.addWidget(self.synch_status, 1, 0, 1, 3)


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
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.note_list.sizePolicy().hasHeightForWidth())
        self.note_list.setSizePolicy(sizePolicy2)
        palette = QPalette()
        self.note_list.setPalette(palette)
        self.note_list.setFont(font2)
        self.note_list.setStyleSheet(u"")

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
        self.scrollArea_5 = QScrollArea(self.project_info)
        self.scrollArea_5.setObjectName(u"scrollArea_5")
        self.scrollArea_5.setWidgetResizable(True)
        self.scrollAreaWidgetContents_11 = QWidget()
        self.scrollAreaWidgetContents_11.setObjectName(u"scrollAreaWidgetContents_11")
        self.scrollAreaWidgetContents_11.setGeometry(QRect(0, 0, 556, 328))
        self.gridLayout_28 = QGridLayout(self.scrollAreaWidgetContents_11)
        self.gridLayout_28.setObjectName(u"gridLayout_28")
        self.label_max_streak = QLabel(self.scrollAreaWidgetContents_11)
        self.label_max_streak.setObjectName(u"label_max_streak")

        self.gridLayout_28.addWidget(self.label_max_streak, 26, 0, 1, 1)

        self.streaks = QLabel(self.scrollAreaWidgetContents_11)
        self.streaks.setObjectName(u"streaks")

        self.gridLayout_28.addWidget(self.streaks, 8, 1, 1, 1)

        self.max_streak = QLabel(self.scrollAreaWidgetContents_11)
        self.max_streak.setObjectName(u"max_streak")

        self.gridLayout_28.addWidget(self.max_streak, 26, 1, 1, 1)

        self.unit_label = QLabel(self.scrollAreaWidgetContents_11)
        self.unit_label.setObjectName(u"unit_label")

        self.gridLayout_28.addWidget(self.unit_label, 23, 0, 1, 1)

        self.today_goal = QLabel(self.scrollAreaWidgetContents_11)
        self.today_goal.setObjectName(u"today_goal")

        self.gridLayout_28.addWidget(self.today_goal, 2, 1, 1, 1)

        self.label_total = QLabel(self.scrollAreaWidgetContents_11)
        self.label_total.setObjectName(u"label_total")

        self.gridLayout_28.addWidget(self.label_total, 3, 0, 1, 1)

        self.deadline = QLabel(self.scrollAreaWidgetContents_11)
        self.deadline.setObjectName(u"deadline")

        self.gridLayout_28.addWidget(self.deadline, 5, 1, 1, 1)

        self.label_status = QLabel(self.scrollAreaWidgetContents_11)
        self.label_status.setObjectName(u"label_status")

        self.gridLayout_28.addWidget(self.label_status, 0, 0, 1, 1)

        self.need = QLabel(self.scrollAreaWidgetContents_11)
        self.need.setObjectName(u"need")

        self.gridLayout_28.addWidget(self.need, 22, 1, 1, 1)

        self.label_streak_status = QLabel(self.scrollAreaWidgetContents_11)
        self.label_streak_status.setObjectName(u"label_streak_status")

        self.gridLayout_28.addWidget(self.label_streak_status, 7, 0, 1, 1)

        self.total = QLabel(self.scrollAreaWidgetContents_11)
        self.total.setObjectName(u"total")

        self.gridLayout_28.addWidget(self.total, 3, 1, 1, 1)

        self.streak_status = QLabel(self.scrollAreaWidgetContents_11)
        self.streak_status.setObjectName(u"streak_status")
        self.streak_status.setWordWrap(True)

        self.gridLayout_28.addWidget(self.streak_status, 7, 1, 1, 1)

        self.added_today = QLabel(self.scrollAreaWidgetContents_11)
        self.added_today.setObjectName(u"added_today")

        self.gridLayout_28.addWidget(self.added_today, 21, 1, 1, 1)

        self.unit = QLabel(self.scrollAreaWidgetContents_11)
        self.unit.setObjectName(u"unit")

        self.gridLayout_28.addWidget(self.unit, 23, 1, 1, 1)

        self.label_need = QLabel(self.scrollAreaWidgetContents_11)
        self.label_need.setObjectName(u"label_need")

        self.gridLayout_28.addWidget(self.label_need, 22, 0, 1, 1)

        self.progress = QLabel(self.scrollAreaWidgetContents_11)
        self.progress.setObjectName(u"progress")

        self.gridLayout_28.addWidget(self.progress, 1, 1, 1, 1)

        self.status = QLabel(self.scrollAreaWidgetContents_11)
        self.status.setObjectName(u"status")

        self.gridLayout_28.addWidget(self.status, 0, 1, 1, 1)

        self.label_today_goal = QLabel(self.scrollAreaWidgetContents_11)
        self.label_today_goal.setObjectName(u"label_today_goal")
        self.label_today_goal.setWordWrap(True)

        self.gridLayout_28.addWidget(self.label_today_goal, 2, 0, 1, 1)

        self.label_streaks = QLabel(self.scrollAreaWidgetContents_11)
        self.label_streaks.setObjectName(u"label_streaks")

        self.gridLayout_28.addWidget(self.label_streaks, 8, 0, 1, 1)

        self.label_deadline = QLabel(self.scrollAreaWidgetContents_11)
        self.label_deadline.setObjectName(u"label_deadline")

        self.gridLayout_28.addWidget(self.label_deadline, 5, 0, 1, 1)

        self.last_note = QLabel(self.scrollAreaWidgetContents_11)
        self.last_note.setObjectName(u"last_note")

        self.gridLayout_28.addWidget(self.last_note, 27, 0, 1, 1)

        self.label_today_added = QLabel(self.scrollAreaWidgetContents_11)
        self.label_today_added.setObjectName(u"label_today_added")

        self.gridLayout_28.addWidget(self.label_today_added, 21, 0, 1, 1)

        self.l = QLabel(self.scrollAreaWidgetContents_11)
        self.l.setObjectName(u"l")
        self.l.setWordWrap(True)

        self.gridLayout_28.addWidget(self.l, 27, 1, 1, 1)

        self.label_progress = QLabel(self.scrollAreaWidgetContents_11)
        self.label_progress.setObjectName(u"label_progress")

        self.gridLayout_28.addWidget(self.label_progress, 1, 0, 1, 1)

        self.label_goal = QLabel(self.scrollAreaWidgetContents_11)
        self.label_goal.setObjectName(u"label_goal")

        self.gridLayout_28.addWidget(self.label_goal, 4, 0, 1, 1)

        self.goal = QLabel(self.scrollAreaWidgetContents_11)
        self.goal.setObjectName(u"goal")

        self.gridLayout_28.addWidget(self.goal, 4, 1, 1, 1)

        self.scrollArea_5.setWidget(self.scrollAreaWidgetContents_11)

        self.gridLayout_2.addWidget(self.scrollArea_5, 0, 0, 1, 1)


        self.gridLayout_4.addWidget(self.project_info, 3, 0, 1, 1)


        self.gridLayout_3.addWidget(self.project_detail_widget, 1, 2, 5, 1)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_3, 5, 1, 1, 1)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_4, 1, 3, 1, 1)

        self.global_streak_status = QLabel(self.projects_tab)
        self.global_streak_status.setObjectName(u"global_streak_status")
        self.global_streak_status.setWordWrap(True)

        self.gridLayout_3.addWidget(self.global_streak_status, 3, 0, 1, 1)

        self.written_today_in_all_projects_label = QLabel(self.projects_tab)
        self.written_today_in_all_projects_label.setObjectName(u"written_today_in_all_projects_label")

        self.gridLayout_3.addWidget(self.written_today_in_all_projects_label, 2, 0, 1, 1)

        self.tabWidget.addTab(self.projects_tab, "")
        self.project_detail_widget.raise_()
        self.btns_create_filter.raise_()
        self.list_projects.raise_()
        self.global_streak_status.raise_()
        self.written_today_in_all_projects_label.raise_()
        self.game_tab = QWidget()
        self.game_tab.setObjectName(u"game_tab")
        self.gridLayout_5 = QGridLayout(self.game_tab)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.game_shop_tabs = QTabWidget(self.game_tab)
        self.game_shop_tabs.setObjectName(u"game_shop_tabs")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.game_shop_tabs.sizePolicy().hasHeightForWidth())
        self.game_shop_tabs.setSizePolicy(sizePolicy3)
        self.game_shop_tabs.setFont(font1)
        self.items_shop_tab = QWidget()
        self.items_shop_tab.setObjectName(u"items_shop_tab")
        self.gridLayout_27 = QGridLayout(self.items_shop_tab)
        self.gridLayout_27.setObjectName(u"gridLayout_27")
        self.item_shop_list = QListWidget(self.items_shop_tab)
        self.item_shop_list.setObjectName(u"item_shop_list")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.item_shop_list.sizePolicy().hasHeightForWidth())
        self.item_shop_list.setSizePolicy(sizePolicy4)
        self.item_shop_list.setMaximumSize(QSize(193, 16777215))
        self.item_shop_list.setFont(font1)

        self.gridLayout_27.addWidget(self.item_shop_list, 0, 0, 1, 1)

        self.selected_goods_item_infobox = QGroupBox(self.items_shop_tab)
        self.selected_goods_item_infobox.setObjectName(u"selected_goods_item_infobox")
        self.selected_goods_item_infobox.setFont(font1)
        self.gridLayout_20 = QGridLayout(self.selected_goods_item_infobox)
        self.gridLayout_20.setObjectName(u"gridLayout_20")
        self.button_for_buy_selected_item = QPushButton(self.selected_goods_item_infobox)
        self.button_for_buy_selected_item.setObjectName(u"button_for_buy_selected_item")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(19)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.button_for_buy_selected_item.sizePolicy().hasHeightForWidth())
        self.button_for_buy_selected_item.setSizePolicy(sizePolicy5)
        self.button_for_buy_selected_item.setFont(font1)
        self.button_for_buy_selected_item.setMouseTracking(False)
        self.button_for_buy_selected_item.setTabletTracking(False)
        self.button_for_buy_selected_item.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.gridLayout_20.addWidget(self.button_for_buy_selected_item, 2, 2, 1, 2)

        self.value_for_buy_selected_item = QSpinBox(self.selected_goods_item_infobox)
        self.value_for_buy_selected_item.setObjectName(u"value_for_buy_selected_item")
        sizePolicy1.setHeightForWidth(self.value_for_buy_selected_item.sizePolicy().hasHeightForWidth())
        self.value_for_buy_selected_item.setSizePolicy(sizePolicy1)
        self.value_for_buy_selected_item.setFont(font1)
        self.value_for_buy_selected_item.setMinimum(1)
        self.value_for_buy_selected_item.setValue(1)

        self.gridLayout_20.addWidget(self.value_for_buy_selected_item, 2, 1, 1, 1)

        self.label_14 = QLabel(self.selected_goods_item_infobox)
        self.label_14.setObjectName(u"label_14")
        sizePolicy1.setHeightForWidth(self.label_14.sizePolicy().hasHeightForWidth())
        self.label_14.setSizePolicy(sizePolicy1)
        self.label_14.setFont(font1)
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_20.addWidget(self.label_14, 2, 0, 1, 1)

        self.about_selected_goods = QScrollArea(self.selected_goods_item_infobox)
        self.about_selected_goods.setObjectName(u"about_selected_goods")
        self.about_selected_goods.setFont(font1)
        self.about_selected_goods.setWidgetResizable(True)
        self.scrollAreaWidgetContents_7 = QWidget()
        self.scrollAreaWidgetContents_7.setObjectName(u"scrollAreaWidgetContents_7")
        self.scrollAreaWidgetContents_7.setGeometry(QRect(0, 0, 405, 131))
        self.gridLayout_21 = QGridLayout(self.scrollAreaWidgetContents_7)
        self.gridLayout_21.setObjectName(u"gridLayout_21")
        self.effect_selected_item_on_shop = QLabel(self.scrollAreaWidgetContents_7)
        self.effect_selected_item_on_shop.setObjectName(u"effect_selected_item_on_shop")
        self.effect_selected_item_on_shop.setFont(font1)
        self.effect_selected_item_on_shop.setWordWrap(True)

        self.gridLayout_21.addWidget(self.effect_selected_item_on_shop, 4, 0, 1, 1)

        self.peice_selected_item_on_shop = QLabel(self.scrollAreaWidgetContents_7)
        self.peice_selected_item_on_shop.setObjectName(u"peice_selected_item_on_shop")
        self.peice_selected_item_on_shop.setFont(font1)
        self.peice_selected_item_on_shop.setWordWrap(True)

        self.gridLayout_21.addWidget(self.peice_selected_item_on_shop, 3, 0, 1, 1)

        self.name_selected_item_on_shop = QLabel(self.scrollAreaWidgetContents_7)
        self.name_selected_item_on_shop.setObjectName(u"name_selected_item_on_shop")
        self.name_selected_item_on_shop.setFont(font1)
        self.name_selected_item_on_shop.setWordWrap(True)

        self.gridLayout_21.addWidget(self.name_selected_item_on_shop, 0, 0, 1, 1)

        self.description_selected_item_on_shop = QLabel(self.scrollAreaWidgetContents_7)
        self.description_selected_item_on_shop.setObjectName(u"description_selected_item_on_shop")
        self.description_selected_item_on_shop.setFont(font1)
        self.description_selected_item_on_shop.setWordWrap(True)

        self.gridLayout_21.addWidget(self.description_selected_item_on_shop, 2, 0, 1, 1)

        self.level_selected_item_on_shop = QLabel(self.scrollAreaWidgetContents_7)
        self.level_selected_item_on_shop.setObjectName(u"level_selected_item_on_shop")
        self.level_selected_item_on_shop.setFont(font1)
        self.level_selected_item_on_shop.setScaledContents(False)
        self.level_selected_item_on_shop.setWordWrap(True)

        self.gridLayout_21.addWidget(self.level_selected_item_on_shop, 1, 0, 1, 1)

        self.about_selected_goods.setWidget(self.scrollAreaWidgetContents_7)

        self.gridLayout_20.addWidget(self.about_selected_goods, 0, 0, 1, 4)


        self.gridLayout_27.addWidget(self.selected_goods_item_infobox, 0, 1, 1, 1)

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
        self.label_12 = QLabel(self.selected_goods_potion_infobox)
        self.label_12.setObjectName(u"label_12")
        sizePolicy1.setHeightForWidth(self.label_12.sizePolicy().hasHeightForWidth())
        self.label_12.setSizePolicy(sizePolicy1)
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_11.addWidget(self.label_12, 2, 0, 1, 1)

        self.button_for_buy_selected_potion = QPushButton(self.selected_goods_potion_infobox)
        self.button_for_buy_selected_potion.setObjectName(u"button_for_buy_selected_potion")
        sizePolicy1.setHeightForWidth(self.button_for_buy_selected_potion.sizePolicy().hasHeightForWidth())
        self.button_for_buy_selected_potion.setSizePolicy(sizePolicy1)

        self.gridLayout_11.addWidget(self.button_for_buy_selected_potion, 2, 2, 1, 2)

        self.value_for_buy_selected_potion = QSpinBox(self.selected_goods_potion_infobox)
        self.value_for_buy_selected_potion.setObjectName(u"value_for_buy_selected_potion")
        sizePolicy1.setHeightForWidth(self.value_for_buy_selected_potion.sizePolicy().hasHeightForWidth())
        self.value_for_buy_selected_potion.setSizePolicy(sizePolicy1)
        self.value_for_buy_selected_potion.setMinimum(1)
        self.value_for_buy_selected_potion.setValue(1)

        self.gridLayout_11.addWidget(self.value_for_buy_selected_potion, 2, 1, 1, 1)

        self.scrollArea_4 = QScrollArea(self.selected_goods_potion_infobox)
        self.scrollArea_4.setObjectName(u"scrollArea_4")
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName(u"scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 93, 112))
        self.gridLayout_18 = QGridLayout(self.scrollAreaWidgetContents_5)
        self.gridLayout_18.setObjectName(u"gridLayout_18")
        self.name_selected_potion_on_shop = QLabel(self.scrollAreaWidgetContents_5)
        self.name_selected_potion_on_shop.setObjectName(u"name_selected_potion_on_shop")
        self.name_selected_potion_on_shop.setWordWrap(True)

        self.gridLayout_18.addWidget(self.name_selected_potion_on_shop, 0, 0, 1, 1)

        self.price_selected_potion_on_shop = QLabel(self.scrollAreaWidgetContents_5)
        self.price_selected_potion_on_shop.setObjectName(u"price_selected_potion_on_shop")
        self.price_selected_potion_on_shop.setWordWrap(True)

        self.gridLayout_18.addWidget(self.price_selected_potion_on_shop, 2, 0, 1, 1)

        self.effect_selected_potion_on_shop = QLabel(self.scrollAreaWidgetContents_5)
        self.effect_selected_potion_on_shop.setObjectName(u"effect_selected_potion_on_shop")
        self.effect_selected_potion_on_shop.setWordWrap(True)

        self.gridLayout_18.addWidget(self.effect_selected_potion_on_shop, 3, 0, 1, 1)

        self.description_selected_potion_on_shop = QLabel(self.scrollAreaWidgetContents_5)
        self.description_selected_potion_on_shop.setObjectName(u"description_selected_potion_on_shop")
        self.description_selected_potion_on_shop.setWordWrap(True)

        self.gridLayout_18.addWidget(self.description_selected_potion_on_shop, 1, 0, 1, 1)

        self.scrollArea_4.setWidget(self.scrollAreaWidgetContents_5)

        self.gridLayout_11.addWidget(self.scrollArea_4, 0, 0, 1, 4)


        self.horizontalLayout.addWidget(self.selected_goods_potion_infobox)

        self.game_shop_tabs.addTab(self.potions_shop_tab, "")
        self.awards_shop_tab = QWidget()
        self.awards_shop_tab.setObjectName(u"awards_shop_tab")
        self.horizontalLayout_3 = QHBoxLayout(self.awards_shop_tab)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.item_shop_list_2 = QListWidget(self.awards_shop_tab)
        self.item_shop_list_2.setObjectName(u"item_shop_list_2")
        sizePolicy4.setHeightForWidth(self.item_shop_list_2.sizePolicy().hasHeightForWidth())
        self.item_shop_list_2.setSizePolicy(sizePolicy4)
        self.item_shop_list_2.setMaximumSize(QSize(193, 16777215))
        self.item_shop_list_2.setFont(font1)

        self.horizontalLayout_3.addWidget(self.item_shop_list_2)

        self.selected_goods_item_infobox_2 = QGroupBox(self.awards_shop_tab)
        self.selected_goods_item_infobox_2.setObjectName(u"selected_goods_item_infobox_2")
        self.selected_goods_item_infobox_2.setFont(font1)
        self.gridLayout_32 = QGridLayout(self.selected_goods_item_infobox_2)
        self.gridLayout_32.setObjectName(u"gridLayout_32")
        self.value_for_buy_selected_item_3 = QSpinBox(self.selected_goods_item_infobox_2)
        self.value_for_buy_selected_item_3.setObjectName(u"value_for_buy_selected_item_3")
        sizePolicy1.setHeightForWidth(self.value_for_buy_selected_item_3.sizePolicy().hasHeightForWidth())
        self.value_for_buy_selected_item_3.setSizePolicy(sizePolicy1)
        self.value_for_buy_selected_item_3.setFont(font1)
        self.value_for_buy_selected_item_3.setMinimum(1)
        self.value_for_buy_selected_item_3.setValue(1)

        self.gridLayout_32.addWidget(self.value_for_buy_selected_item_3, 2, 1, 1, 1)

        self.label_16 = QLabel(self.selected_goods_item_infobox_2)
        self.label_16.setObjectName(u"label_16")
        sizePolicy1.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy1)
        self.label_16.setFont(font1)
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_32.addWidget(self.label_16, 2, 0, 1, 1)

        self.about_selected_goods_3 = QScrollArea(self.selected_goods_item_infobox_2)
        self.about_selected_goods_3.setObjectName(u"about_selected_goods_3")
        self.about_selected_goods_3.setFont(font1)
        self.about_selected_goods_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_12 = QWidget()
        self.scrollAreaWidgetContents_12.setObjectName(u"scrollAreaWidgetContents_12")
        self.scrollAreaWidgetContents_12.setGeometry(QRect(0, 0, 90, 110))
        self.gridLayout_33 = QGridLayout(self.scrollAreaWidgetContents_12)
        self.gridLayout_33.setObjectName(u"gridLayout_33")
        self.peice_selected_custom_award_on_shop = QLabel(self.scrollAreaWidgetContents_12)
        self.peice_selected_custom_award_on_shop.setObjectName(u"peice_selected_custom_award_on_shop")
        self.peice_selected_custom_award_on_shop.setFont(font1)
        self.peice_selected_custom_award_on_shop.setWordWrap(True)

        self.gridLayout_33.addWidget(self.peice_selected_custom_award_on_shop, 1, 0, 1, 1)

        self.name_selected_custom_award_on_shop = QLabel(self.scrollAreaWidgetContents_12)
        self.name_selected_custom_award_on_shop.setObjectName(u"name_selected_custom_award_on_shop")
        self.name_selected_custom_award_on_shop.setFont(font1)
        self.name_selected_custom_award_on_shop.setWordWrap(True)

        self.gridLayout_33.addWidget(self.name_selected_custom_award_on_shop, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_33.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.about_selected_goods_3.setWidget(self.scrollAreaWidgetContents_12)

        self.gridLayout_32.addWidget(self.about_selected_goods_3, 0, 0, 1, 7)

        self.button_for_buy_selected_item_3 = QPushButton(self.selected_goods_item_infobox_2)
        self.button_for_buy_selected_item_3.setObjectName(u"button_for_buy_selected_item_3")
        sizePolicy5.setHeightForWidth(self.button_for_buy_selected_item_3.sizePolicy().hasHeightForWidth())
        self.button_for_buy_selected_item_3.setSizePolicy(sizePolicy5)
        self.button_for_buy_selected_item_3.setFont(font1)
        self.button_for_buy_selected_item_3.setMouseTracking(False)
        self.button_for_buy_selected_item_3.setTabletTracking(False)
        self.button_for_buy_selected_item_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.gridLayout_32.addWidget(self.button_for_buy_selected_item_3, 3, 0, 1, 1)

        self.button_for_create_custom_award = QPushButton(self.selected_goods_item_infobox_2)
        self.button_for_create_custom_award.setObjectName(u"button_for_create_custom_award")

        self.gridLayout_32.addWidget(self.button_for_create_custom_award, 3, 1, 1, 1)

        self.button_for_edit_selected_custom_award = QPushButton(self.selected_goods_item_infobox_2)
        self.button_for_edit_selected_custom_award.setObjectName(u"button_for_edit_selected_custom_award")

        self.gridLayout_32.addWidget(self.button_for_edit_selected_custom_award, 3, 2, 1, 1)

        self.button_for_delete_selected_custom_award = QPushButton(self.selected_goods_item_infobox_2)
        self.button_for_delete_selected_custom_award.setObjectName(u"button_for_delete_selected_custom_award")

        self.gridLayout_32.addWidget(self.button_for_delete_selected_custom_award, 3, 3, 1, 1)


        self.horizontalLayout_3.addWidget(self.selected_goods_item_infobox_2)

        self.game_shop_tabs.addTab(self.awards_shop_tab, "")

        self.gridLayout_5.addWidget(self.game_shop_tabs, 4, 1, 1, 1)

        self.shop_label = QLabel(self.game_tab)
        self.shop_label.setObjectName(u"shop_label")
        self.shop_label.setFont(font1)
        self.shop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.shop_label, 3, 1, 1, 1)

        self.inventory_frame = QFrame(self.game_tab)
        self.inventory_frame.setObjectName(u"inventory_frame")
        sizePolicy3.setHeightForWidth(self.inventory_frame.sizePolicy().hasHeightForWidth())
        self.inventory_frame.setSizePolicy(sizePolicy3)
        self.inventory_frame.setFont(font1)
        self.inventory_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.inventory_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.inventory_frame)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.inventory_list = QListWidget(self.inventory_frame)
        self.inventory_list.setObjectName(u"inventory_list")
        sizePolicy.setHeightForWidth(self.inventory_list.sizePolicy().hasHeightForWidth())
        self.inventory_list.setSizePolicy(sizePolicy)
        self.inventory_list.setMaximumSize(QSize(193, 16777215))
        self.inventory_list.setFont(font1)

        self.horizontalLayout_5.addWidget(self.inventory_list)

        self.inventory_scroll_area = QGroupBox(self.inventory_frame)
        self.inventory_scroll_area.setObjectName(u"inventory_scroll_area")
        self.inventory_scroll_area.setFont(font1)
        self.gridLayout_12 = QGridLayout(self.inventory_scroll_area)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.button_for_selected_item = QPushButton(self.inventory_scroll_area)
        self.button_for_selected_item.setObjectName(u"button_for_selected_item")
        sizePolicy1.setHeightForWidth(self.button_for_selected_item.sizePolicy().hasHeightForWidth())
        self.button_for_selected_item.setSizePolicy(sizePolicy1)
        self.button_for_selected_item.setFont(font1)

        self.gridLayout_12.addWidget(self.button_for_selected_item, 3, 2, 1, 2)

        self.label_13 = QLabel(self.inventory_scroll_area)
        self.label_13.setObjectName(u"label_13")
        sizePolicy1.setHeightForWidth(self.label_13.sizePolicy().hasHeightForWidth())
        self.label_13.setSizePolicy(sizePolicy1)
        self.label_13.setFont(font1)
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_13, 3, 0, 1, 1)

        self.value_for_use_selected_item = QSpinBox(self.inventory_scroll_area)
        self.value_for_use_selected_item.setObjectName(u"value_for_use_selected_item")
        sizePolicy1.setHeightForWidth(self.value_for_use_selected_item.sizePolicy().hasHeightForWidth())
        self.value_for_use_selected_item.setSizePolicy(sizePolicy1)
        self.value_for_use_selected_item.setFont(font1)
        self.value_for_use_selected_item.setMinimum(1)
        self.value_for_use_selected_item.setSingleStep(1)
        self.value_for_use_selected_item.setValue(1)

        self.gridLayout_12.addWidget(self.value_for_use_selected_item, 3, 1, 1, 1)

        self.about_selected_inventory_item = QScrollArea(self.inventory_scroll_area)
        self.about_selected_inventory_item.setObjectName(u"about_selected_inventory_item")
        self.about_selected_inventory_item.setFont(font1)
        self.about_selected_inventory_item.setWidgetResizable(True)
        self.scrollAreaWidgetContents_6 = QWidget()
        self.scrollAreaWidgetContents_6.setObjectName(u"scrollAreaWidgetContents_6")
        self.scrollAreaWidgetContents_6.setGeometry(QRect(0, 0, 409, 150))
        self.gridLayout_19 = QGridLayout(self.scrollAreaWidgetContents_6)
        self.gridLayout_19.setObjectName(u"gridLayout_19")
        self.name_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.name_selected_item.setObjectName(u"name_selected_item")
        self.name_selected_item.setFont(font1)
        self.name_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.name_selected_item, 0, 0, 1, 1)

        self.level_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.level_selected_item.setObjectName(u"level_selected_item")
        self.level_selected_item.setFont(font1)
        self.level_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.level_selected_item, 2, 0, 1, 1)

        self.effect_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.effect_selected_item.setObjectName(u"effect_selected_item")
        self.effect_selected_item.setFont(font1)
        self.effect_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.effect_selected_item, 3, 0, 1, 1)

        self.description_selected_item = QLabel(self.scrollAreaWidgetContents_6)
        self.description_selected_item.setObjectName(u"description_selected_item")
        self.description_selected_item.setFont(font1)
        self.description_selected_item.setWordWrap(True)

        self.gridLayout_19.addWidget(self.description_selected_item, 1, 0, 1, 1)

        self.about_selected_inventory_item.setWidget(self.scrollAreaWidgetContents_6)

        self.gridLayout_12.addWidget(self.about_selected_inventory_item, 0, 0, 1, 4)


        self.horizontalLayout_5.addWidget(self.inventory_scroll_area)


        self.gridLayout_5.addWidget(self.inventory_frame, 2, 1, 1, 1)

        self.gamer_params_label = QLabel(self.game_tab)
        self.gamer_params_label.setObjectName(u"gamer_params_label")
        self.gamer_params_label.setMaximumSize(QSize(16777215, 18))
        self.gamer_params_label.setFont(font1)
        self.gamer_params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.gamer_params_label, 1, 0, 1, 1)

        self.frame_5 = QFrame(self.game_tab)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy6)
        self.frame_5.setMinimumSize(QSize(0, 100))
        self.frame_5.setFont(font1)
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_6 = QGridLayout(self.frame_5)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gamer_health = QLabel(self.frame_5)
        self.gamer_health.setObjectName(u"gamer_health")
        self.gamer_health.setFont(font1)
        self.gamer_health.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_health, 0, 3, 1, 1)

        self.gamer_exp = QLabel(self.frame_5)
        self.gamer_exp.setObjectName(u"gamer_exp")
        self.gamer_exp.setFont(font1)
        self.gamer_exp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_exp, 0, 2, 1, 1)

        self.gamer_coins = QLabel(self.frame_5)
        self.gamer_coins.setObjectName(u"gamer_coins")
        self.gamer_coins.setFont(font1)
        self.gamer_coins.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_coins, 1, 1, 1, 1)

        self.exp_progressbar = QProgressBar(self.frame_5)
        self.exp_progressbar.setObjectName(u"exp_progressbar")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.exp_progressbar.sizePolicy().hasHeightForWidth())
        self.exp_progressbar.setSizePolicy(sizePolicy7)
        self.exp_progressbar.setFont(font1)
        self.exp_progressbar.setValue(24)

        self.gridLayout_6.addWidget(self.exp_progressbar, 1, 2, 1, 1)

        self.gamer_health_progressbar = QProgressBar(self.frame_5)
        self.gamer_health_progressbar.setObjectName(u"gamer_health_progressbar")
        sizePolicy7.setHeightForWidth(self.gamer_health_progressbar.sizePolicy().hasHeightForWidth())
        self.gamer_health_progressbar.setSizePolicy(sizePolicy7)
        self.gamer_health_progressbar.setFont(font1)
        self.gamer_health_progressbar.setValue(24)

        self.gridLayout_6.addWidget(self.gamer_health_progressbar, 1, 3, 1, 1)

        self.label_3 = QLabel(self.frame_5)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label_3, 0, 1, 1, 1)

        self.label = QLabel(self.frame_5)
        self.label.setObjectName(u"label")
        self.label.setFont(font1)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.label, 0, 0, 1, 1)

        self.gamer_label = QLabel(self.frame_5)
        self.gamer_label.setObjectName(u"gamer_label")
        self.gamer_label.setFont(font1)
        self.gamer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_6.addWidget(self.gamer_label, 1, 0, 1, 1)

        self.bank_btn = QPushButton(self.frame_5)
        self.bank_btn.setObjectName(u"bank_btn")
        sizePolicy1.setHeightForWidth(self.bank_btn.sizePolicy().hasHeightForWidth())
        self.bank_btn.setSizePolicy(sizePolicy1)
        self.bank_btn.setFont(font1)

        self.gridLayout_6.addWidget(self.bank_btn, 2, 1, 1, 1)


        self.gridLayout_5.addWidget(self.frame_5, 0, 0, 1, 2)

        self.inventory_label = QLabel(self.game_tab)
        self.inventory_label.setObjectName(u"inventory_label")
        self.inventory_label.setFont(font1)
        self.inventory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.inventory_label, 1, 1, 1, 1)

        self.quests_label = QLabel(self.game_tab)
        self.quests_label.setObjectName(u"quests_label")
        self.quests_label.setMaximumSize(QSize(16777215, 18))
        self.quests_label.setFont(font1)
        self.quests_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_5.addWidget(self.quests_label, 3, 0, 1, 1)

        self.quests_tabs = QTabWidget(self.game_tab)
        self.quests_tabs.setObjectName(u"quests_tabs")
        sizePolicy3.setHeightForWidth(self.quests_tabs.sizePolicy().hasHeightForWidth())
        self.quests_tabs.setSizePolicy(sizePolicy3)
        self.quests_tabs.setFont(font1)
        self.available_quests_tab = QWidget()
        self.available_quests_tab.setObjectName(u"available_quests_tab")
        self.gridLayout_8 = QGridLayout(self.available_quests_tab)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.available_quests_list = QListWidget(self.available_quests_tab)
        self.available_quests_list.setObjectName(u"available_quests_list")
        sizePolicy4.setHeightForWidth(self.available_quests_list.sizePolicy().hasHeightForWidth())
        self.available_quests_list.setSizePolicy(sizePolicy4)
        self.available_quests_list.setMaximumSize(QSize(193, 16777215))
        self.available_quests_list.setFont(font1)

        self.gridLayout_8.addWidget(self.available_quests_list, 0, 0, 1, 1)

        self.about_selected_available_quest = QGroupBox(self.available_quests_tab)
        self.about_selected_available_quest.setObjectName(u"about_selected_available_quest")
        self.about_selected_available_quest.setFont(font1)
        self.gridLayout_13 = QGridLayout(self.about_selected_available_quest)
        self.gridLayout_13.setObjectName(u"gridLayout_13")
        self.scrollArea_3 = QScrollArea(self.about_selected_available_quest)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setFont(font1)
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 357, 131))
        self.gridLayout_14 = QGridLayout(self.scrollAreaWidgetContents_4)
        self.gridLayout_14.setObjectName(u"gridLayout_14")
        self.name_selected_available_quest = QLabel(self.scrollAreaWidgetContents_4)
        self.name_selected_available_quest.setObjectName(u"name_selected_available_quest")
        self.name_selected_available_quest.setFont(font1)
        self.name_selected_available_quest.setWordWrap(True)

        self.gridLayout_14.addWidget(self.name_selected_available_quest, 0, 0, 1, 1)

        self.description_selected_available_quest = QLabel(self.scrollAreaWidgetContents_4)
        self.description_selected_available_quest.setObjectName(u"description_selected_available_quest")
        self.description_selected_available_quest.setFont(font1)
        self.description_selected_available_quest.setWordWrap(True)

        self.gridLayout_14.addWidget(self.description_selected_available_quest, 1, 0, 1, 1)

        self.prize_selected_available_quest = QLabel(self.scrollAreaWidgetContents_4)
        self.prize_selected_available_quest.setObjectName(u"prize_selected_available_quest")
        self.prize_selected_available_quest.setFont(font1)
        self.prize_selected_available_quest.setWordWrap(True)

        self.gridLayout_14.addWidget(self.prize_selected_available_quest, 2, 0, 1, 1)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_4)

        self.gridLayout_13.addWidget(self.scrollArea_3, 2, 1, 1, 1)

        self.button_for_start_selected_quest = QPushButton(self.about_selected_available_quest)
        self.button_for_start_selected_quest.setObjectName(u"button_for_start_selected_quest")
        sizePolicy1.setHeightForWidth(self.button_for_start_selected_quest.sizePolicy().hasHeightForWidth())
        self.button_for_start_selected_quest.setSizePolicy(sizePolicy1)
        self.button_for_start_selected_quest.setFont(font1)

        self.gridLayout_13.addWidget(self.button_for_start_selected_quest, 3, 1, 1, 1)


        self.gridLayout_8.addWidget(self.about_selected_available_quest, 0, 1, 1, 1)

        self.quests_tabs.addTab(self.available_quests_tab, "")
        self.active_quests_tab = QWidget()
        self.active_quests_tab.setObjectName(u"active_quests_tab")
        self.gridLayout_9 = QGridLayout(self.active_quests_tab)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.active_quests_list = QListWidget(self.active_quests_tab)
        self.active_quests_list.setObjectName(u"active_quests_list")
        sizePolicy4.setHeightForWidth(self.active_quests_list.sizePolicy().hasHeightForWidth())
        self.active_quests_list.setSizePolicy(sizePolicy4)
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
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 100, 168))
        self.gridLayout_17 = QGridLayout(self.scrollAreaWidgetContents_3)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.date_start_selected_active_quest = QLabel(self.scrollAreaWidgetContents_3)
        self.date_start_selected_active_quest.setObjectName(u"date_start_selected_active_quest")
        self.date_start_selected_active_quest.setWordWrap(True)

        self.gridLayout_17.addWidget(self.date_start_selected_active_quest, 3, 0, 1, 1)

        self.name_selected_active_quest = QLabel(self.scrollAreaWidgetContents_3)
        self.name_selected_active_quest.setObjectName(u"name_selected_active_quest")
        self.name_selected_active_quest.setWordWrap(True)

        self.gridLayout_17.addWidget(self.name_selected_active_quest, 0, 0, 1, 1)

        self.description_selected_active_quest = QLabel(self.scrollAreaWidgetContents_3)
        self.description_selected_active_quest.setObjectName(u"description_selected_active_quest")
        self.description_selected_active_quest.setWordWrap(True)

        self.gridLayout_17.addWidget(self.description_selected_active_quest, 1, 0, 1, 1)

        self.date_end_selected_active_quest = QLabel(self.scrollAreaWidgetContents_3)
        self.date_end_selected_active_quest.setObjectName(u"date_end_selected_active_quest")
        self.date_end_selected_active_quest.setWordWrap(True)

        self.gridLayout_17.addWidget(self.date_end_selected_active_quest, 4, 0, 1, 1)

        self.prize_selected_active_quest = QLabel(self.scrollAreaWidgetContents_3)
        self.prize_selected_active_quest.setObjectName(u"prize_selected_active_quest")
        self.prize_selected_active_quest.setWordWrap(True)

        self.gridLayout_17.addWidget(self.prize_selected_active_quest, 2, 0, 1, 1)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout.addWidget(self.scrollArea_2)

        self.button_for_stop_selected_quest = QPushButton(self.about_selected_active_quest)
        self.button_for_stop_selected_quest.setObjectName(u"button_for_stop_selected_quest")
        sizePolicy1.setHeightForWidth(self.button_for_stop_selected_quest.sizePolicy().hasHeightForWidth())
        self.button_for_stop_selected_quest.setSizePolicy(sizePolicy1)

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
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 100, 168))
        self.gridLayout_16 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_16.setObjectName(u"gridLayout_16")
        self.date_end_selected_completed_quest = QLabel(self.scrollAreaWidgetContents_2)
        self.date_end_selected_completed_quest.setObjectName(u"date_end_selected_completed_quest")
        self.date_end_selected_completed_quest.setWordWrap(True)

        self.gridLayout_16.addWidget(self.date_end_selected_completed_quest, 4, 0, 1, 1)

        self.prize_selected_completed_quest = QLabel(self.scrollAreaWidgetContents_2)
        self.prize_selected_completed_quest.setObjectName(u"prize_selected_completed_quest")
        self.prize_selected_completed_quest.setWordWrap(True)

        self.gridLayout_16.addWidget(self.prize_selected_completed_quest, 2, 0, 1, 1)

        self.description_selected_completed_quest = QLabel(self.scrollAreaWidgetContents_2)
        self.description_selected_completed_quest.setObjectName(u"description_selected_completed_quest")
        self.description_selected_completed_quest.setWordWrap(True)

        self.gridLayout_16.addWidget(self.description_selected_completed_quest, 1, 0, 1, 1)

        self.name_selected_completed_quest = QLabel(self.scrollAreaWidgetContents_2)
        self.name_selected_completed_quest.setObjectName(u"name_selected_completed_quest")
        self.name_selected_completed_quest.setWordWrap(True)

        self.gridLayout_16.addWidget(self.name_selected_completed_quest, 0, 0, 1, 1)

        self.date_start_selected_completed_quest = QLabel(self.scrollAreaWidgetContents_2)
        self.date_start_selected_completed_quest.setObjectName(u"date_start_selected_completed_quest")
        self.date_start_selected_completed_quest.setWordWrap(True)

        self.gridLayout_16.addWidget(self.date_start_selected_completed_quest, 3, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_15.addWidget(self.scrollArea, 0, 1, 1, 1)


        self.gridLayout_10.addWidget(self.about_selected_completed_quest, 0, 1, 1, 1)

        self.quests_tabs.addTab(self.completed_quests_tab, "")

        self.gridLayout_5.addWidget(self.quests_tabs, 4, 0, 1, 1)

        self.parameters_tabs = QTabWidget(self.game_tab)
        self.parameters_tabs.setObjectName(u"parameters_tabs")
        sizePolicy3.setHeightForWidth(self.parameters_tabs.sizePolicy().hasHeightForWidth())
        self.parameters_tabs.setSizePolicy(sizePolicy3)
        self.parameters_tabs.setFont(font1)
        self.bufs_tab = QWidget()
        self.bufs_tab.setObjectName(u"bufs_tab")
        self.horizontalLayout_7 = QHBoxLayout(self.bufs_tab)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.buf_list = QListWidget(self.bufs_tab)
        self.buf_list.setObjectName(u"buf_list")
        sizePolicy4.setHeightForWidth(self.buf_list.sizePolicy().hasHeightForWidth())
        self.buf_list.setSizePolicy(sizePolicy4)
        self.buf_list.setMaximumSize(QSize(193, 16777215))
        self.buf_list.setFont(font1)

        self.horizontalLayout_7.addWidget(self.buf_list)

        self.about_selected_buf = QGroupBox(self.bufs_tab)
        self.about_selected_buf.setObjectName(u"about_selected_buf")
        self.about_selected_buf.setFont(font1)
        self.gridLayout_22 = QGridLayout(self.about_selected_buf)
        self.gridLayout_22.setObjectName(u"gridLayout_22")
        self.scrollArea_7 = QScrollArea(self.about_selected_buf)
        self.scrollArea_7.setObjectName(u"scrollArea_7")
        self.scrollArea_7.setFont(font1)
        self.scrollArea_7.setWidgetResizable(True)
        self.scrollAreaWidgetContents_8 = QWidget()
        self.scrollAreaWidgetContents_8.setObjectName(u"scrollAreaWidgetContents_8")
        self.scrollAreaWidgetContents_8.setGeometry(QRect(0, 0, 357, 159))
        self.gridLayout_23 = QGridLayout(self.scrollAreaWidgetContents_8)
        self.gridLayout_23.setObjectName(u"gridLayout_23")
        self.label_37 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_37.setObjectName(u"label_37")
        self.label_37.setFont(font1)
        self.label_37.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_37, 4, 0, 1, 1)

        self.label_38 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_38.setObjectName(u"label_38")
        self.label_38.setFont(font1)
        self.label_38.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_38, 2, 0, 1, 1)

        self.label_39 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_39.setObjectName(u"label_39")
        self.label_39.setFont(font1)
        self.label_39.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_39, 1, 0, 1, 1)

        self.label_40 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_40.setObjectName(u"label_40")
        self.label_40.setFont(font1)
        self.label_40.setWordWrap(True)

        self.gridLayout_23.addWidget(self.label_40, 0, 0, 1, 1)

        self.label_41 = QLabel(self.scrollAreaWidgetContents_8)
        self.label_41.setObjectName(u"label_41")
        self.label_41.setFont(font1)
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
        self.scrollAreaWidgetContents_9.setGeometry(QRect(0, 0, 357, 161))
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
        self.gamer_parameters_tab = QWidget()
        self.gamer_parameters_tab.setObjectName(u"gamer_parameters_tab")
        self.horizontalLayout_4 = QHBoxLayout(self.gamer_parameters_tab)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.gamer_parameters_list = QListWidget(self.gamer_parameters_tab)
        self.gamer_parameters_list.setObjectName(u"gamer_parameters_list")
        sizePolicy.setHeightForWidth(self.gamer_parameters_list.sizePolicy().hasHeightForWidth())
        self.gamer_parameters_list.setSizePolicy(sizePolicy)
        self.gamer_parameters_list.setMaximumSize(QSize(193, 16777215))

        self.horizontalLayout_4.addWidget(self.gamer_parameters_list)

        self.groupBox = QGroupBox(self.gamer_parameters_tab)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.scrollArea_6 = QScrollArea(self.groupBox)
        self.scrollArea_6.setObjectName(u"scrollArea_6")
        self.scrollArea_6.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 357, 161))
        self.verticalLayout_4 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.description_selected_parameter = QLabel(self.scrollAreaWidgetContents)
        self.description_selected_parameter.setObjectName(u"description_selected_parameter")
        self.description_selected_parameter.setWordWrap(True)

        self.verticalLayout_4.addWidget(self.description_selected_parameter)

        self.scrollArea_6.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_3.addWidget(self.scrollArea_6)


        self.horizontalLayout_4.addWidget(self.groupBox)

        self.parameters_tabs.addTab(self.gamer_parameters_tab, "")
        self.skills_tab = QWidget()
        self.skills_tab.setObjectName(u"skills_tab")
        self.gridLayout_7 = QGridLayout(self.skills_tab)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.productivity_skill_points = QSpinBox(self.skills_tab)
        self.productivity_skill_points.setObjectName(u"productivity_skill_points")
        sizePolicy1.setHeightForWidth(self.productivity_skill_points.sizePolicy().hasHeightForWidth())
        self.productivity_skill_points.setSizePolicy(sizePolicy1)
        self.productivity_skill_points.setFont(font1)
        self.productivity_skill_points.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.productivity_skill_points, 3, 0, 1, 1)

        self.skill_description_profitability = QLabel(self.skills_tab)
        self.skill_description_profitability.setObjectName(u"skill_description_profitability")
        self.skill_description_profitability.setFont(font1)
        self.skill_description_profitability.setWordWrap(True)

        self.gridLayout_7.addWidget(self.skill_description_profitability, 2, 1, 1, 1)

        self.label_7 = QLabel(self.skills_tab)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setFont(font1)
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.label_7, 1, 1, 1, 1)

        self.endurance_skill_description = QLabel(self.skills_tab)
        self.endurance_skill_description.setObjectName(u"endurance_skill_description")
        self.endurance_skill_description.setFont(font1)
        self.endurance_skill_description.setWordWrap(True)

        self.gridLayout_7.addWidget(self.endurance_skill_description, 2, 2, 1, 1)

        self.skill_points_profitability = QSpinBox(self.skills_tab)
        self.skill_points_profitability.setObjectName(u"skill_points_profitability")
        sizePolicy1.setHeightForWidth(self.skill_points_profitability.sizePolicy().hasHeightForWidth())
        self.skill_points_profitability.setSizePolicy(sizePolicy1)
        font4 = QFont()
        font4.setFamilies([u"Arial"])
        font4.setHintingPreference(QFont.PreferDefaultHinting)
        self.skill_points_profitability.setFont(font4)
        self.skill_points_profitability.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.skill_points_profitability.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.skill_points_profitability, 3, 1, 1, 1)

        self.skill_description_productivity = QLabel(self.skills_tab)
        self.skill_description_productivity.setObjectName(u"skill_description_productivity")
        self.skill_description_productivity.setFont(font1)
        self.skill_description_productivity.setWordWrap(True)

        self.gridLayout_7.addWidget(self.skill_description_productivity, 2, 0, 1, 1)

        self.label_8 = QLabel(self.skills_tab)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setFont(font1)
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.label_8, 1, 2, 1, 1)

        self.endurance_skill_points = QSpinBox(self.skills_tab)
        self.endurance_skill_points.setObjectName(u"endurance_skill_points")
        sizePolicy8 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(0)
        sizePolicy8.setHeightForWidth(self.endurance_skill_points.sizePolicy().hasHeightForWidth())
        self.endurance_skill_points.setSizePolicy(sizePolicy8)
        self.endurance_skill_points.setFont(font1)
        self.endurance_skill_points.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.endurance_skill_points, 3, 2, 1, 1)

        self.label_6 = QLabel(self.skills_tab)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font1)
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.label_6, 1, 0, 1, 1)

        self.available_skill_points = QLabel(self.skills_tab)
        self.available_skill_points.setObjectName(u"available_skill_points")
        self.available_skill_points.setFont(font1)

        self.gridLayout_7.addWidget(self.available_skill_points, 0, 1, 1, 1)

        self.parameters_tabs.addTab(self.skills_tab, "")

        self.gridLayout_5.addWidget(self.parameters_tabs, 2, 0, 1, 1)

        self.tabWidget.addTab(self.game_tab, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        main_window.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(main_window)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1380, 30))
        self.settings_menu = QMenu(self.menuBar)
        self.settings_menu.setObjectName(u"settings_menu")
        self.project_menu = QMenu(self.menuBar)
        self.project_menu.setObjectName(u"project_menu")
        main_window.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.settings_menu.menuAction())
        self.menuBar.addAction(self.project_menu.menuAction())
        self.project_menu.addAction(self.synch_action)
        self.project_menu.addAction(self.del_synch_action)
        self.project_menu.addAction(self.create_project_action)
        self.project_menu.addAction(self.change_project_action)
        self.project_menu.addAction(self.project_stats_action)
        self.project_menu.addAction(self.archive_project_action)
        self.project_menu.addAction(self.complete_project_action)
        self.project_menu.addAction(self.delete_project_action)

        self.retranslateUi(main_window)

        self.tabWidget.setCurrentIndex(1)
        self.game_shop_tabs.setCurrentIndex(0)
        self.quests_tabs.setCurrentIndex(0)
        self.parameters_tabs.setCurrentIndex(3)


        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"nfprogress", None))
        self.synch_action.setText(QCoreApplication.translate("main_window", u"\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c", None))
        self.del_synch_action.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e", None))
        self.delete_project_action.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.change_project_action.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.create_project_action.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.project_stats_action.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u043f\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0443", None))
        self.archive_project_action.setText(QCoreApplication.translate("main_window", u"\u0410\u0440\u0445\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.complete_project_action.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.sort_project_box.setItemText(0, QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.sort_project_box.setItemText(1, QCoreApplication.translate("main_window", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d", None))
        self.sort_project_box.setItemText(2, QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441", None))

        self.label_5.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0430 \u043f\u043e \u0441\u0432\u043e\u0439\u0441\u0442\u0432\u0443:", None))
        self.label_4.setText(QCoreApplication.translate("main_window", u"\u0424\u0438\u043b\u044c\u0442\u0440 \u043f\u043e \u0441\u0442\u0430\u0442\u0443\u0441\u0443:", None))
        self.filter_project_box.setItemText(0, QCoreApplication.translate("main_window", u"\u0410\u043a\u0442\u0438\u0432\u0435\u043d", None))
        self.filter_project_box.setItemText(1, QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432\u0435", None))
        self.filter_project_box.setItemText(2, QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d", None))

        self.btn_create_project.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.name_selected_project.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0440\u043e\u0435\u043a\u0442", None))
        self.btn_change_project.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.btn_delete_project.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.btn_synch_project.setText(QCoreApplication.translate("main_window", u"\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c", None))
        self.btn_archived_project.setText(QCoreApplication.translate("main_window", u"\u0412 \u0430\u0440\u0445\u0438\u0432", None))
        self.btn_complete_project.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c", None))
        self.synch_status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d", None))
        self.label_2.setText(QCoreApplication.translate("main_window", u"\u0417\u0430\u043f\u0438\u0441\u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", None))
        self.label_9.setText(QCoreApplication.translate("main_window", u"\u041d\u043e\u0432\u0430\u044f \u0437\u0430\u043f\u0438\u0441\u044c:", None))
        self.delete_note.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.pb_save_flash_note.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c", None))
        self.project_info.setTitle(QCoreApplication.translate("main_window", u"\u0418\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f \u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.label_max_streak.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.streaks.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.max_streak.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.unit_label.setText(QCoreApplication.translate("main_window", u"\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f:", None))
        self.today_goal.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_total.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435:", None))
        self.deadline.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_status.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u0430\u0442\u0443\u0441:", None))
        self.need.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_streak_status.setText(QCoreApplication.translate("main_window", u"C\u0442\u0430\u0442\u0443\u0441 \u0441\u0442\u0440\u0438\u043a\u0430:", None))
        self.total.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.streak_status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.added_today.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.unit.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_need.setText(QCoreApplication.translate("main_window", u"\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043d\u0430\u043f\u0438\u0441\u0430\u0442\u044c: ", None))
        self.progress.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.status.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_today_goal.setText(QCoreApplication.translate("main_window", u"<html><head/><body><p>\u0426\u0435\u043b\u044c \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f:</p></body></html>", None))
        self.label_streaks.setText(QCoreApplication.translate("main_window", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a: ", None))
        self.label_deadline.setText(QCoreApplication.translate("main_window", u"\u0414\u0435\u0434\u043b\u0430\u0439\u043d:", None))
        self.last_note.setText(QCoreApplication.translate("main_window", u"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0437\u0430\u043f\u0438\u0441\u044c: ", None))
        self.label_today_added.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f:", None))
        self.l.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.label_progress.setText(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.label_goal.setText(QCoreApplication.translate("main_window", u"\u0426\u0435\u043b\u044c \u043f\u0440\u043e\u0435\u043a\u0442\u0430:", None))
        self.goal.setText(QCoreApplication.translate("main_window", u"\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438", None))
        self.global_streak_status.setText(QCoreApplication.translate("main_window", u"\u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0440\u0438\u043a", None))
        self.written_today_in_all_projects_label.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u0441\u0435\u0433\u043e\u0434\u043d\u044f", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.projects_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0435\u043a\u0442\u044b", None))
        self.selected_goods_item_infobox.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.button_for_buy_selected_item.setText(QCoreApplication.translate("main_window", u"\u041a\u0443\u043f\u0438\u0442\u044c", None))
        self.label_14.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.effect_selected_item_on_shop.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.peice_selected_item_on_shop.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.name_selected_item_on_shop.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.description_selected_item_on_shop.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.level_selected_item_on_shop.setText(QCoreApplication.translate("main_window", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c", None))
        self.game_shop_tabs.setTabText(self.game_shop_tabs.indexOf(self.items_shop_tab), QCoreApplication.translate("main_window", u"\u041f\u0440\u0435\u0434\u043c\u0435\u0442\u044b", None))
        self.selected_goods_potion_infobox.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.label_12.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.button_for_buy_selected_potion.setText(QCoreApplication.translate("main_window", u"\u041a\u0443\u043f\u0438\u0442\u044c", None))
        self.name_selected_potion_on_shop.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.price_selected_potion_on_shop.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.effect_selected_potion_on_shop.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.description_selected_potion_on_shop.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.game_shop_tabs.setTabText(self.game_shop_tabs.indexOf(self.potions_shop_tab), QCoreApplication.translate("main_window", u"\u0417\u0435\u043b\u044c\u044f", None))
        self.selected_goods_item_infobox_2.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.label_16.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.peice_selected_custom_award_on_shop.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.name_selected_custom_award_on_shop.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.button_for_buy_selected_item_3.setText(QCoreApplication.translate("main_window", u"\u041a\u0443\u043f\u0438\u0442\u044c", None))
        self.button_for_create_custom_award.setText(QCoreApplication.translate("main_window", u"\u0421\u043e\u0437\u0434\u0430\u0442\u044c", None))
        self.button_for_edit_selected_custom_award.setText(QCoreApplication.translate("main_window", u"\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c", None))
        self.button_for_delete_selected_custom_award.setText(QCoreApplication.translate("main_window", u"\u0423\u0434\u0430\u043b\u0438\u0442\u044c", None))
        self.game_shop_tabs.setTabText(self.game_shop_tabs.indexOf(self.awards_shop_tab), QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u044b", None))
        self.shop_label.setText(QCoreApplication.translate("main_window", u"\u041c\u0430\u0433\u0430\u0437\u0438\u043d", None))
        self.inventory_scroll_area.setTitle(QCoreApplication.translate("main_window", u"\u041e \u0442\u043e\u0432\u0430\u0440\u0435", None))
        self.button_for_selected_item.setText(QCoreApplication.translate("main_window", u"\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c", None))
        self.label_13.setText(QCoreApplication.translate("main_window", u"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e:", None))
        self.name_selected_item.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.level_selected_item.setText(QCoreApplication.translate("main_window", u"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c", None))
        self.effect_selected_item.setText(QCoreApplication.translate("main_window", u"\u042d\u0444\u0444\u0435\u043a\u0442\u044b", None))
        self.description_selected_item.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.gamer_params_label.setText(QCoreApplication.translate("main_window", u"\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430", None))
        self.gamer_health.setText(QCoreApplication.translate("main_window", u"\u0417\u0434\u043e\u0440\u043e\u0432\u044c\u0435 100/100", None))
        self.gamer_exp.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u044b\u0442: 0/100", None))
        self.gamer_coins.setText(QCoreApplication.translate("main_window", u"0", None))
        self.label_3.setText(QCoreApplication.translate("main_window", u"\u041c\u043e\u043d\u0435\u0442\u044b", None))
        self.label.setText(QCoreApplication.translate("main_window", u"\u0423\u0440\u043e\u0432\u0435\u043d\u044c", None))
        self.gamer_label.setText(QCoreApplication.translate("main_window", u"1", None))
        self.bank_btn.setText(QCoreApplication.translate("main_window", u"\u0411\u0430\u043d\u043a", None))
        self.inventory_label.setText(QCoreApplication.translate("main_window", u"\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u044c", None))
        self.quests_label.setText(QCoreApplication.translate("main_window", u"\u041a\u0432\u0435\u0441\u0442\u044b", None))
        self.about_selected_available_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.name_selected_available_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.description_selected_available_quest.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.prize_selected_available_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.button_for_start_selected_quest.setText(QCoreApplication.translate("main_window", u"\u0412\u0437\u044f\u0442\u044c \u043a\u0432\u0435\u0441\u0442", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.available_quests_tab), QCoreApplication.translate("main_window", u"\u0414\u043e\u0441\u0442\u0443\u043f\u044b\u043d\u0435", None))
        self.about_selected_active_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.date_start_selected_active_quest.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.name_selected_active_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.description_selected_active_quest.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.date_end_selected_active_quest.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.prize_selected_active_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.button_for_stop_selected_quest.setText(QCoreApplication.translate("main_window", u"\u041e\u0442\u043a\u0430\u0437\u0430\u0442\u044c\u0441\u044f \u043e\u0442 \u043a\u0432\u0435\u0441\u0442\u0430", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.active_quests_tab), QCoreApplication.translate("main_window", u"\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435", None))
        self.about_selected_completed_quest.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043a\u0432\u0435\u0441\u0442\u0435", None))
        self.date_end_selected_completed_quest.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f", None))
        self.prize_selected_completed_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0433\u0440\u0430\u0434\u0430", None))
        self.description_selected_completed_quest.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435", None))
        self.name_selected_completed_quest.setText(QCoreApplication.translate("main_window", u"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", None))
        self.date_start_selected_completed_quest.setText(QCoreApplication.translate("main_window", u"\u0414\u0430\u0442\u0430 \u043d\u0430\u0447\u0430\u043b\u0430", None))
        self.quests_tabs.setTabText(self.quests_tabs.indexOf(self.completed_quests_tab), QCoreApplication.translate("main_window", u"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043d\u044b\u0435", None))
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
        self.groupBox.setTitle(QCoreApplication.translate("main_window", u"\u041e \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u0435", None))
        self.description_selected_parameter.setText(QCoreApplication.translate("main_window", u"\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u0430", None))
        self.parameters_tabs.setTabText(self.parameters_tabs.indexOf(self.gamer_parameters_tab), QCoreApplication.translate("main_window", u"\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u0436\u0430", None))
        self.skill_description_profitability.setText(QCoreApplication.translate("main_window", u"\u0412\u043e\u0438\u044f\u0435\u0442 \u043d\u0430 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u043c\u044b\u0445 \u043c\u043e\u043d\u0435\u0442", None))
        self.label_7.setText(QCoreApplication.translate("main_window", u"\u0414\u043e\u0445\u043e\u0434\u043d\u043e\u0441\u0442\u044c", None))
        self.endurance_skill_description.setText(QCoreApplication.translate("main_window", u"\u0412\u043b\u0438\u044f\u0435\u0442 \u043d\u0430 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0437\u0434\u043e\u0440\u043e\u0432\u044c\u044f", None))
        self.skill_description_productivity.setText(QCoreApplication.translate("main_window", u"\u0412\u043b\u0438\u044f\u0435\u0442 \u043d\u0430 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u043c\u043e\u0433\u043e \u043e\u043f\u044b\u0442\u0430", None))
        self.label_8.setText(QCoreApplication.translate("main_window", u"\u0412\u044b\u043d\u043e\u0441\u043b\u0438\u0432\u043e\u0441\u0442\u044c", None))
        self.label_6.setText(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0434\u0443\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u044c", None))
        self.available_skill_points.setText(QCoreApplication.translate("main_window", u"\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0431\u0430\u043b\u043b\u044b \u0443\u043c\u0435\u043d\u0438\u0439: 0", None))
        self.parameters_tabs.setTabText(self.parameters_tabs.indexOf(self.skills_tab), QCoreApplication.translate("main_window", u"\u0423\u043c\u0435\u043d\u0438\u044f", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.game_tab), QCoreApplication.translate("main_window", u"\u0418\u0433\u0440\u043e\u0432\u043e\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.settings_menu.setTitle(QCoreApplication.translate("main_window", u"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", None))
        self.project_menu.setTitle(QCoreApplication.translate("main_window", u"\u041f\u0440\u043e\u0435\u043a\u0442", None))
    # retranslateUi

