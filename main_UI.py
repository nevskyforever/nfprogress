import datetime
import math
import os
import sys
import threading

from PySide6.QtCore import QObject, QTranslator, QLibraryInfo, QDate, QTimer, Qt, QCborKnownTags, QThread, Signal, Slot, QRectF, QSize
from PySide6.QtGui import QKeySequence, QImage, QPainter, QColor, QPen, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow, QDialog, QListWidgetItem, QFileDialog, QVBoxLayout, QTreeWidget, \
    QTreeWidgetItem, QDialogButtonBox, QLabel, QMessageBox

import engine as en
import game
from UI_fiiles.confirm_dialog import Ui_confirm_dialog as confirm_dialog_ui
from UI_fiiles.create_project import Ui_create_project as create_project_ui
from UI_fiiles.developer_mode import Ui_developer_node
from UI_fiiles.main_window import Ui_main_window as main_window_ui
from UI_fiiles.notification import ToastNotification
from UI_fiiles.project_widget import ProjectWidget, StageRowWidget
from UI_fiiles.settings import Ui_Dialog as settings_ui
from UI_fiiles.synch_window import Ui_sych_window
from UI_fiiles.user_agreement import Ui_user_agreement as user_agreement_ui
from UI_fiiles.project_stats import Ui_project_stats as project_stats_ui
from engine import save_data, save_settings, load_settings
from game_UI import GameMenuController
from scrivener_parser import find_scrivener_xml, parse_scrivener_items, count_symbols_in_scrivener_item
from update_checker import UpdateChecker, run_windows_updater_from_argv


def _read_word_sync_source(project):
    file_path = project.synch['path']
    if not os.path.exists(file_path):
        return None, None, 'missing'

    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        symbols = en.count_symbols_in_docx(file_path)
    elif ext == '.doc':
        return None, None, 'doc_unsupported'
    else:
        return None, None, 'unsupported_format'

    file_mtime = os.path.getmtime(file_path)
    note_date = datetime.datetime.fromtimestamp(file_mtime)
    return symbols, note_date, None


def _read_scrivener_sync_source(project):
    proj_path = project.synch['path']
    item_id = project.synch['item_id']
    if not os.path.exists(proj_path):
        return None, None, 'missing'

    symbols = count_symbols_in_scrivener_item(proj_path, item_id)
    proj_mtime = os.path.getmtime(proj_path)
    note_date = datetime.datetime.fromtimestamp(proj_mtime)
    return symbols, note_date, None


class SyncReadWorker(QObject):
    finished = Signal(object, str, object, object, object, bool, object)
    failed = Signal(object, str, str, bool, object)

    def __init__(self, project, sync_type, background_synch=False, batch_id=None):
        super().__init__()
        self.project = project
        self.sync_type = sync_type
        self.background_synch = background_synch
        self.batch_id = batch_id

    @Slot()
    def run(self):
        try:
            if self.sync_type == 'word':
                symbols, note_date, read_error = _read_word_sync_source(self.project)
            elif self.sync_type == 'scrivener':
                symbols, note_date, read_error = _read_scrivener_sync_source(self.project)
            else:
                symbols, note_date, read_error = None, None, 'unsupported_sync_type'
        except Exception as error:
            self.failed.emit(
                self.project,
                self.sync_type,
                str(error),
                self.background_synch,
                self.batch_id
            )
            return

        self.finished.emit(
            self.project,
            self.sync_type,
            symbols,
            note_date,
            read_error,
            self.background_synch,
            self.batch_id
        )


class MainWindow(QMainWindow, main_window_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Создаем менеджер уведомлений
        self.notifications = NotificationManager(self)

        # Инициализация игрового контроллера
        self.game_controller = GameMenuController(self, self.notifications)
        self.developer_mode_action = None

        self.unit_to_display = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }

        # для отслеживания предыдущей вкладки
        self._previous_tab = None
        # были ли уже подключены обработчики кнопок проекта (setup_project_buttons)
        self._project_buttons_connected = False
        self._sync_threads = {}
        self._background_sync_batches = {}
        self._expanded_stage_projects = set()
        self.update_checker = None
        self.create_stage_action = self.project_menu.addAction('Создать этап')
        self.create_stage_action.triggered.connect(self.create_stage)
        self.create_stage_action.setEnabled(False)

        # Применяем настройки
        self.applying_settings()
        self.global_streak_mode = en.load_settings().get('global_streak', False)
        self.filter_project_box.setCurrentText(en.load_settings().get('project_filter', 'Активен'))
        self.sort_project_box.setCurrentText(en.load_settings().get('project_sort', 'Прогресс'))

        # Проверяем пользовательское соглашение
        if not en.dev_mode:
            self.check_user_agreement()

        # Обновляем проекты
        self.background_synch()
        self.refresh_projects()

        # Подключаем обработчик изменения фильтра
        self.filter_project_box.currentTextChanged.connect(self.on_filter_changed)
        self.sort_project_box.currentTextChanged.connect(self.on_sort_changed)

        # Подключаем обработчик переключения вкладок
        self.tabWidget.currentChanged.connect(self.on_tab_changed)


        # Правильный способ подключения кнопки
        self.project_info.setVisible(False)
        self.note_widget.setVisible(False)
        self.change_project_widget.setVisible(False)
        self.btn_create_project.clicked.connect(self.create_project)
        self.list_projects.itemClicked.connect(self.view_project)

        # Подключаем обработку Enter для поля ввода
        self.new_symbols.returnPressed.connect(self.on_enter_pressed)

        # Добавляем менюбар
        # Настройки
        self.settings_menu.addAction("Настройки приложения").triggered.connect(self.edit_settings)
        if self.global_streak_mode:
            self.refresh_global_streak_status()
            QTimer.singleShot(1000, self.check_global_streak)

        # Подключение действий меню "Проект"
        self.synch_action.triggered.connect(self.on_sync_menu_triggered)
        self.synch_action.setShortcut(QKeySequence.StandardKey.Save)

        self.del_synch_action.triggered.connect(self.on_delete_sync_menu_triggered)

        self.create_project_action.triggered.connect(self.create_project)
        self.create_project_action.setShortcut(QKeySequence.StandardKey.New)

        self.change_project_action.triggered.connect(self.on_change_project_menu_triggered)
        self.change_project_action.setShortcut(QKeySequence("Ctrl+E"))

        self.delete_project_action.triggered.connect(self.on_delete_project_menu_triggered)
        self.delete_project_action.setShortcut(QKeySequence.StandardKey.Delete)

        # === НОВЫЕ ПОДКЛЮЧЕНИЯ ===
        self.project_stats_action.triggered.connect(self.show_project_stats)
        self.project_stats_action.setShortcut(QKeySequence('Ctrl+Shift+S'))  # лучше Ctrl+S для статистики

        self.archive_project_action.triggered.connect(self.on_archive_project_menu_triggered)
        self.archive_project_action.setShortcut(QKeySequence('Ctrl+Shift+H'))  # H от "Hide" / "Archive"

        self.complete_project_action.triggered.connect(self.on_complete_project_menu_triggered)
        self.complete_project_action.setShortcut(QKeySequence('Ctrl+Shift+C'))

        # Открываем последний проект
        if en.load_settings().get('last_project', False):
            self.show_last_project(en.load_settings()['last_project'])

        # Фоновая проверка системной даты/времени для автообновления UI
        self._setup_time_watcher()

    def closeEvent(self, event):
        """Останавливает все активные анимации перед уничтожением окна.

        Иначе при закрытии приложения Qt рвёт дерево виджетов, пока
        QVariantAnimation/QPropertyAnimation ещё тикают (круговые прогресс-бары
        проектов, fade-анимации тостов), и shiboken печатает в консоль
        "Called attribute on invalid object" для уже удалённых объектов.
        """
        for i in range(self.list_projects.count()):
            widget = self.list_projects.itemWidget(self.list_projects.item(i))
            if widget is not None and hasattr(widget, 'stop_animations'):
                widget.stop_animations()

        # Сбрасываем текущее выделение: нативная (macOS) анимация подсветки
        # выбранного элемента списка может ещё проигрываться в момент закрытия
        # окна — тогда она тикает на уже уничтоженных объектах.
        self.list_projects.clearSelection()
        self.list_projects.setCurrentItem(None)
        self.note_list.clearSelection()
        self.note_list.setCurrentItem(None)

        for toast in list(self.notifications.toasts):
            toast.fade_in_anim.stop()
            toast.fade_out_anim.stop()

        for project_name in list(self._sync_threads):
            self._cleanup_sync_read_worker(project_name)

        if self.update_checker is not None:
            self.update_checker.shutdown()

        super().closeEvent(event)

    def _setup_time_watcher(self):
        """Запускает таймер, который периодически проверяет системное время."""
        self._last_effective_date = en.today_for_test()
        self._last_checked_minute = datetime.datetime.now().replace(second=0, microsecond=0)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(60_000)  # 1 раз в минуту
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._clock_timer.start()

    def _on_clock_tick(self):
        """Обновляет проекты при смене даты, чтобы дедлайны/стрики не требовали перезапуска."""
        current_minute = datetime.datetime.now().replace(second=0, microsecond=0)
        current_effective_date = en.today_for_test()

        # Защита от лишних обновлений, если тикер сработал в ту же минуту
        if current_minute == self._last_checked_minute:
            return
        self._last_checked_minute = current_minute

        if current_effective_date == self._last_effective_date:
            return

        self._refresh_for_effective_date_change(current_effective_date, show_notification=True)

    def _refresh_for_effective_date_change(self, current_effective_date=None, show_notification=False):
        """Обновляет состояние приложения после смены эффективной даты."""
        if current_effective_date is None:
            current_effective_date = en.today_for_test()

        self._last_effective_date = current_effective_date
        # На смене даты запускаем фоновую синхронизацию только для активных синхронизированных проектов.
        self.background_synch(silent=True)
        self.refresh_projects()

        current_project = self.get_current_project()
        if current_project is not None:
            self.show_project_info(current_project)
            self.setup_project_buttons(current_project)

        if en.load_settings().get('global_streak', False):
            self.refresh_global_streak_status()

        self.game_controller.process_bank_events(show_toasts=True)
        self.game_controller.update_game_data()
        if show_notification:
            self.notifications.show_info('Новый день. Проекты обновлены.', position='bottom-right')

    def on_enter_pressed(self):
        """Обработчик нажатия Enter в поле ввода"""
        # Получаем текущий выбранный проект
        current_item = self.list_projects.currentItem()
        if current_item is None:
            return

        # Получаем виджет проекта
        widget = self.list_projects.itemWidget(current_item)
        if widget and hasattr(widget, 'project'):
            # Получаем проект и добавляем заметку
            project = widget.project
            self.add_note(project)

    def create_project(self):
        """Создаёт новый проект."""
        data = en.load_data()
        dialog = CreateProject(existing_names=data['projects'].keys())
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()

            name = dialog.get_name()
            goal = dialog.get_goal()
            total = dialog.get_total()
            unit = dialog.get_unit()
            deadline = dialog.get_deadline()
            personal_goal_for_the_day = dialog.get_personal_goal_for_the_day()

            # Проверяем, что проект с таким именем не существует
            if name in data['projects']:
                self.notifications.show_error(f'Проект "{name}" уже существует!')
                return
            if unit != 'author_list':
                goal = math.ceil(goal)
                total = math.ceil(total)

            new_project = en.Project(
                name=name,
                goal=goal,
                deadline=deadline,
                total_symbols=total,
                unit=unit,
                personal_goal_for_the_day=personal_goal_for_the_day
            )
            if dialog.is_stages_enabled():
                pending_stages = dialog.get_pending_stages()
                if pending_stages:
                    new_project.enable_stages = True
                    new_project.stages = pending_stages
                    new_project.notes = []
                    new_project.synch = None
                    for stage in new_project.stages:
                        stage.parent_project_name = new_project.name
                        stage.unit = new_project.unit
                else:
                    new_project.convert_to_stages()

            # Если это бесконечный проект (inf_project), устанавливаем goal = inf
            if en.load_settings().get('inf_project', False) and name == 'Общий проект':
                new_project.goal = float('inf')

            # Считаем цель на день
            new_project.get_today_goal_value()
            data['projects'][new_project.name] = new_project
            en.save_data(data)

            self.refresh_projects()

            # Выделяем созданный проект
            self.select_project_by_name(new_project.name)
            self.view_project()

            unit_name = self._get_unit_name(unit)
            self.notifications.show_success(
                f"Проект '{name}' создан! (Цель: {goal} {unit_name})",
                2000,
                "bottom-left"
            )

    def create_stage(self):
        """Создаёт новый этап внутри выбранного проекта с этапами."""
        current_project = self.get_current_project()
        if current_project is None:
            self.notifications.show_warning("Сначала выберите проект с этапами")
            return

        data = en.load_data()
        if self._is_stage(current_project):
            parent, _ = self._find_stage_parent(data, current_project)
        else:
            parent = data['projects'].get(current_project.name)

        if parent is None or not getattr(parent, 'has_stages', lambda: False)():
            self.notifications.show_warning("Этап можно создать только в проекте с этапами")
            return

        dialog = CreateProject(
            parent=self,
            existing_names=[stage.name for stage in parent.stages],
            stage_mode=True,
            fixed_unit=parent.unit,
        )
        result = dialog.exec()

        if result != QDialog.Accepted:
            return

        name = dialog.get_name()
        goal = dialog.get_goal()
        total = dialog.get_total()
        unit = parent.unit
        deadline = dialog.get_deadline()
        personal_goal_for_the_day = dialog.get_personal_goal_for_the_day()

        if name in [stage.name for stage in parent.stages]:
            self.notifications.show_error(f'Этап "{name}" уже существует!')
            return
        if unit != 'author_list':
            goal = math.ceil(goal)
            total = math.ceil(total)

        stage = en.Stage(
            name=name,
            goal=goal,
            deadline=deadline,
            total_symbols=total,
            unit=unit,
            personal_goal_for_the_day=personal_goal_for_the_day,
            parent_project_name=parent.name,
        )
        stage.get_today_goal_value()
        parent.stages.append(stage)
        data['projects'][parent.name] = parent
        en.save_data(data)

        self._expanded_stage_projects.add(parent.name)
        self.refresh_projects()
        self.select_stage_by_id(parent.name, stage.stage_id)
        self.view_project()
        self.notifications.show_success(f'Этап "{name}" создан!', position="bottom-left")

    def applying_settings(self):
        settings = en.load_settings()

        # 1. СНАЧАЛА находим индекс игровой вкладки (если она есть)
        game_tab_index = -1
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == 'Игровой режим':
                game_tab_index = i
                break

        # 2. Обработка игрового режима
        if not settings['game_mode']:
            # Режим выключен
            if game_tab_index >= 0:
                # Сохраняем виджет ПЕРЕД удалением
                self.game_tab_widget = self.tabWidget.widget(game_tab_index)
                self.tabWidget.removeTab(game_tab_index)

            # Удаляем пункт меню "Режим разработчика", если он существует
            if self.developer_mode_action:
                self.settings_menu.removeAction(self.developer_mode_action)
                self.developer_mode_action = None
        else:
            # Режим включен
            if game_tab_index < 0:
                # Вкладки нет - добавляем
                if hasattr(self, 'game_tab_widget') and self.game_tab_widget:
                    # Используем сохранённый виджет
                    self.tabWidget.addTab(self.game_tab_widget, 'Игровой режим')
                else:
                    # Создаём новую вкладку (используем существующую из UI)
                    self.tabWidget.addTab(self.game_tab, 'Игровой режим')

        # Добавляем/удаляем пункт меню "Режим разработчика" в зависимости от режима разработчика
        if en.dev_mode:
            if not self.developer_mode_action:
                self.developer_mode_action = self.settings_menu.addAction('Режим разработчика')
                self.developer_mode_action.setShortcut(QKeySequence('Ctrl+D'))
                self.developer_mode_action.triggered.connect(self.developer_mode)
        else:
            if self.developer_mode_action:
                self.settings_menu.removeAction(self.developer_mode_action)
                self.developer_mode_action = None

        data = en.load_data()
        projects = data['projects']
        data_changed = False

        if settings.get('inf_project'):
            # 1. Если есть старый ключ, мигрируем данные
            if 'inf_project' in projects:
                old_inf_project = projects['inf_project']
                old_inf_project.name = 'Общий проект'  # Обновляем имя внутри объекта проекта
                projects['Общий проект'] = old_inf_project
                del projects['inf_project']
                data_changed = True

            # 2. Если старого ключа нет И нового еще не создано — создаем с нуля
            elif 'Общий проект' not in projects:
                inf_project = en.Project(name='Общий проект', goal=float('inf'), progress=100)
                projects['Общий проект'] = inf_project
                data_changed = True
        else:
            if projects.get('Общий проект', False):
                del projects['Общий проект']
                data_changed = True
            if projects.get('inf_project', False):
                del projects['inf_project']
                data_changed = True

        if data_changed:
            save_data(data)

        self.global_streak_status.setVisible(settings.get('global_streak', False))
        self.refresh_projects()
        self.view_project()
        if settings.get('show_written_today_in_all_projects'):
            self.written_today_in_all_projects_label.setVisible(True)
            self.written_today_in_all_projects()
        else:
            self.written_today_in_all_projects_label.setVisible(False)

    def edit_settings(self):
        dialog = Settings()
        result = dialog.exec()
        if result == QDialog.Accepted:
                inf_project = dialog.enable_inf_projects_checkBox.isChecked()
                game_mode = dialog.enable_game_mode_checkBox.isChecked()
                global_streak = dialog.enable_global_streak_checkBox.isChecked()
                show_written_today_in_all_projects = dialog.written_today_in_all_projects_checkBox.isChecked()
                notification_display_time = dialog.notification_display_time_spinBox.value()
                settings = en.load_settings()
                settings['inf_project'] = inf_project
                settings['game_mode'] = game_mode
                settings['global_streak'] = global_streak
                settings['show_written_today_in_all_projects'] = show_written_today_in_all_projects
                settings['notification_display_time'] = notification_display_time
                if not global_streak:
                    data = en.load_data()
                    data['global_streaks'] = []
                    data['global_streak_status'] = 'No'
                    data['max_global_streak'] = 0
                    data['last_global_streak_bonus'] = None
                    data['last_global_streak_lost_date'] = None
                    for p in data['projects'].values():
                        p.streaks = []
                        p.streak_status = 'No'
                        for stage in getattr(p, 'stages', []):
                            stage.streaks = []
                            stage.streak_status = 'No'
                    en.save_data(data)
                en.save_settings(settings)
        self.applying_settings()

    def view_project(self):
        """Отображает информацию о выбранном проекте"""
        # Получаем текущий выбранный элемент
        current_item = self.list_projects.currentItem()

        if current_item is None:
            # Если ничего не выбрано, скрываем панели
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.name_selected_project.setText("Выберите проект")
            self.create_stage_action.setEnabled(False)
            return

        # Получаем виджет, связанный с выбранным элементом
        widget = self.list_projects.itemWidget(current_item)

        if widget is None or not hasattr(widget, 'project'):
            self.project_info.setVisible(False)
            return

        # Получаем проект из виджета
        project = widget.project

        # Отображаем информацию о проекте
        self.show_project_info(project)

        # Настраиваем кнопки управления
        self.setup_project_buttons(project)

        # Показываем панели
        self.project_info.setVisible(True)
        self.note_widget.setVisible(True)
        self.change_project_widget.setVisible(True)
        self.name_selected_project.setText(project.name)

        # Сохраняем последний выбранный проект
        settings = en.load_settings()
        settings['last_project'] = project.name
        save_settings(settings)

    def show_project_info(self, project: en.Project):
        """Заполняет виджеты информацией о проекте."""
        units_for_view = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }

        # Обрабатыааем бесконечный проект
        if project.goal == float('inf'):
            self.label_deadline.setVisible(False)
            self.deadline.setVisible(False)
            self.label_max_streak.setVisible(False)
            self.max_streak.setVisible(False)
            self.label_progress.setVisible(False)
            self.progress.setVisible(False)
        else:
            self.label_progress.setVisible(True)
            self.progress.setVisible(True)

        # Основная информация
        self.status.setText(project.status)
        self.progress.setText(f"{project.progress:.1f}%")
        # Обрабатываем бесконечный проект
        if project.goal == float('inf'):
            self.goal.setText('∞')
        else:
            self.goal.setText(self._format_number(project.goal))
        self.total.setText(self._format_number(project.total_units))
        self.unit.setText(units_for_view[project.unit])

        # Статистика за сегодня (в единице проекта)
        added_today = project.get_added_today_in_unit()
        self.added_today.setText(self._format_number(added_today))

        # Осталось написать (в единице проекта)
        need = project.get_need_write_in_unit()
        if need == float('inf') or project.goal == float('inf'):
            self.need.setText('∞')
            self.today_goal.setVisible(False)
            self.label_today_goal.setVisible(False)
        else:
            self.need.setText(self._format_number(need))

        # Дедлайн и цель на сегодня
        has_stage_daily_goal = (
                getattr(project, 'has_stages', lambda: False)()
                and project.get_today_goal_value() > 0
        )
        if project.deadline != 'Нет' or has_stage_daily_goal:
            self.label_deadline.setVisible(True)
            self.deadline.setVisible(True)
            self.label_today_goal.setVisible(True)
            self.today_goal.setVisible(True)

            # Цель на сегодня (в единице проекта)
            if project.goal == float('inf'):
                self.today_goal.setVisible(False)
                self.label_today_goal.setVisible(False)
            else:
                # Всегда показываем цель, если есть дедлайн (независимо от personal_goal)
                if project.get_total_symbols() >= project.get_today_goal_value():
                    self.today_goal.setText(
                        f'Цель на сегодня выполнена! ({self._format_number_for_unit(project.get_today_goal_in_unit(), project.unit)})')
                else:
                    self.today_goal.setText(self._format_number_for_unit(project.get_today_goal_in_unit(), project.unit))

            if project.deadline != 'Нет':
                self.deadline.setText(project.deadline_str)
                # Расчёт оставшихся дней
                days_left = (project.deadline - en.today_for_test()).days
                if days_left > 0:
                    self.deadline.setText(f"{project.deadline_str} (осталось {days_left} дн.)")
                elif days_left == 0:
                    self.deadline.setText(f"{project.deadline_str} (сегодня!)")
                else:
                    self.deadline.setText(f"{project.deadline_str} (просрочено на {abs(days_left)} дн.)")
            else:
                self.deadline.setText("Не установлен")
        else:
            self.label_today_goal.setVisible(False)
            self.today_goal.setVisible(False)
            self.deadline.setText("Не установлен")

        # Информация о стриках
        show_streak = en.load_settings().get('global_streak', False) and self._project_can_show_streak(project)
        if show_streak:
            self.label_streaks.setVisible(True)
            self.label_streak_status.setVisible(True)
            self.label_max_streak.setVisible(True)
            self.streaks.setVisible(True)
            self.max_streak.setVisible(True)
            self.streak_status.setVisible(True)

            self.streaks.setText(str(en.streak_length(project.streaks)))
            self.max_streak.setText(str(project.max_streak))
            self.streak_status.setText(project.get_streak_status_msg('min'))
        else:
            self.label_streaks.setVisible(False)
            self.label_streak_status.setVisible(False)
            self.label_max_streak.setVisible(False)
            self.streaks.setVisible(False)
            self.max_streak.setVisible(False)
            self.streak_status.setVisible(False)

        # Последняя запись (если есть)
        stage_name, last_note = project.get_latest_note()
        if last_note:
            added_disp = en.unit_converter('symbols', last_note.added_symbols, project.unit)
            stage_prefix = f"{stage_name}: " if stage_name else ""
            self.l.setText(f"{stage_prefix}{last_note.get_date_create_str()} (+{self._format_number(added_disp)})")
        else:
            self.l.setText("Нет записей")


    def show_last_project(self, project_name):
        self.select_project_by_name(project_name)
        self.view_project()

    def show_project_stats(self):
        """Открывает окно статистики для текущего выбранного проекта"""
        project = self.get_current_project()  # у тебя уже есть этот метод

        if project is None:
            self.notifications.show_warning("Сначала выберите проект!")
            return

        dialog = ProjectStatsDialog(project, self)
        dialog.exec()

    def _format_number(self, num):
        """Форматирует число для отображения."""
        if isinstance(num, float):
            if num.is_integer():
                return str(int(num))
            # Оставляем 1-2 знака после запятой, убираем лишние нули
            return f"{num:.2f}".rstrip('0').rstrip('.') if '.' in f"{num:.2f}" else str(int(num))
        return str(num)

    def _format_number_for_unit(self, num, unit):
        """Форматирует число для отображения с учётом единицы измерения."""
        if unit == 'author_list':
            # Проверяем, целое ли число (с учётом погрешности float)
            if abs(num - round(num)) < 1e-9:
                return str(int(round(num)))
            else:
                return f"{num:.1f}"
        else:
            return self._format_number(num)

    def select_project_by_name(self, project_name):
        """Выделяет проект по имени в списке"""
        for i in range(self.list_projects.count()):
            item = self.list_projects.item(i)
            widget = self.list_projects.itemWidget(item)
            if widget and hasattr(widget, 'project') and widget.project.name == project_name:
                self.list_projects.setCurrentItem(item)
                # Обновляем отображение информации, используя проект из виджета
                self.show_project_info(widget.project)
                self.setup_project_buttons(widget.project)
                # 👇 Добавляем обновление имени выбранного проекта
                self.name_selected_project.setText(project_name)
                break

    def select_stage_by_id(self, parent_name, stage_id):
        self._expanded_stage_projects.add(parent_name)
        for i in range(self.list_projects.count()):
            item = self.list_projects.item(i)
            widget = self.list_projects.itemWidget(item)
            if (
                    widget and hasattr(widget, 'project') and
                    getattr(widget.project, 'stage_id', None) == stage_id
            ):
                self.list_projects.setCurrentItem(item)
                self.show_project_info(widget.project)
                self.setup_project_buttons(widget.project)
                self.name_selected_project.setText(widget.project.name)
                break

    def setup_project_buttons(self, project):
        """Настраивает кнопки управления проектом"""
        # Отключаем старые соединения только если они действительно были
        # установлены — иначе PySide печатает RuntimeWarning "Failed to
        # disconnect (None) from signal", даже если TypeError перехвачен.
        if self._project_buttons_connected:
            self.btn_change_project.clicked.disconnect()
            self.btn_complete_project.clicked.disconnect()
            self.btn_archived_project.clicked.disconnect()
            self.btn_delete_project.clicked.disconnect()
            self.pb_save_flash_note.clicked.disconnect()
            self.delete_note.clicked.disconnect()
            self.btn_synch_project.clicked.disconnect()
            self.share_progress.clicked.disconnect()

        self._project_buttons_connected = True

        # Подключаем новые
        self.btn_change_project.clicked.connect(lambda: self.edit_project(project))
        self.btn_complete_project.clicked.connect(lambda: self.complete_project(project))
        self.btn_archived_project.clicked.connect(lambda: self.archive_project(project))
        self.btn_delete_project.clicked.connect(lambda: self.delete_project(project))
        self.pb_save_flash_note.clicked.connect(lambda: self.add_note(project))
        self.pb_save_flash_note.clicked.connect(lambda: self.refresh_global_streak_status())
        self.delete_note.clicked.connect(lambda: self.delete_selected_note(project))
        self.btn_synch_project.clicked.connect(lambda: self.sync_project(project))
        self.share_progress.clicked.connect(lambda: self.share_project_progress(project))
        # Включение/отключение действия удаления синхронизации в меню
        has_stage_sync = (
                getattr(project, 'has_stages', lambda: False)() and
                any(stage.synch is not None for stage in project.stages)
        )
        self.del_synch_action.setEnabled(project.synch is not None or has_stage_sync)
        parent_for_stage_action = self._get_parent_project(project) if self._is_stage(project) else project
        self.create_stage_action.setEnabled(getattr(parent_for_stage_action, 'has_stages', lambda: False)())

        # Устанавливаем состояние кнопок в зависимости от статуса проекта
        self.change_project_widget.setEnabled(True)

        if project.status == 'завершен' and not en.dev_mode:
            # Проект завершён — отключаем изменение, повторное завершение, архивацию и работу с заметками
            self.btn_change_project.setEnabled(False)
            self.btn_complete_project.setEnabled(False)
            self.btn_archived_project.setEnabled(False)
            self.btn_delete_project.setEnabled(True)  # удаление обычно разрешено
            self.pb_save_flash_note.setEnabled(False)
            self.delete_note.setEnabled(False)
            self.new_symbols.setEnabled(False)  # отключаем поле ввода
        else:
            # Проект активен или в архиве — настраиваем кнопки по логике
            self.btn_change_project.setEnabled(True)
            self.change_project_action.setEnabled(True)
            self.archive_project_action.setEnabled(True)
            # Кнопка завершения активна, если цель достигнута
            self.btn_complete_project.setEnabled(project.goal <= project.total_units)
            self.complete_project_action.setEnabled(project.goal <= project.total_units)

            # Меняем текст кнопки в зависимости от статуса
            if project.status == 'в архиве':
                self.btn_archived_project.setText('Активировать')
            else:
                self.btn_archived_project.setText('В архив')

            self.btn_archived_project.setEnabled(not self._is_stage(project))
            self.archive_project_action.setEnabled(not self._is_stage(project))
            self.btn_delete_project.setEnabled(True)

            # Логика для ручного добавления записей:
            # Если синхронизация включена (project.synch не None), отключаем ручное добавление
            if getattr(project, 'has_stages', lambda: False)():
                self.pb_save_flash_note.setEnabled(False)
                self.new_symbols.setEnabled(False)
                self.delete_note.setEnabled(False)
                self.new_symbols.setPlaceholderText("Выберите этап")
            elif project.synch is not None:
                self.pb_save_flash_note.setEnabled(False)
                self.new_symbols.setEnabled(False)
                self.delete_note.setEnabled(True)  # удаление записей всё ещё разрешено
                # Добавляем подсказку для пользователя
                self.new_symbols.setPlaceholderText("Включена синхронизация")
            else:
                self.pb_save_flash_note.setEnabled(True)
                self.new_symbols.setEnabled(True)
                self.delete_note.setEnabled(True)
                self.new_symbols.setPlaceholderText("")
        if project.goal == float('inf') and not en.dev_mode:
            self.btn_change_project.setEnabled(False)
            self.btn_complete_project.setEnabled(False)
            self.change_project_action.setEnabled(False)
            self.complete_project_action.setEnabled(False)
            self.delete_project_action.setEnabled(False)
            self.btn_delete_project.setEnabled(False)
            self.archive_project_action.setEnabled(False)
            self.btn_archived_project.setEnabled(False)

        # Загружаем список заметок
        self.load_notes(project)

        # Обновляем статус синхронизации
        self.update_sync_status_label(project)

    def _project_can_show_streak(self, project):
        if self._is_stage(project):
            parent_project = self._get_parent_project(project)
            return (
                    parent_project is not None
                    and parent_project.deadline == 'Нет'
                    and project.deadline != 'Нет'
            )
        return project.deadline != 'Нет'

    def _get_streak_bonus_project(self, data, project):
        if not self._is_stage(project):
            project.get_streak_status()
            return project

        parent_project, _ = self._find_stage_parent(data, project)
        if parent_project is not None and parent_project.deadline != 'Нет':
            parent_project.get_streak_status()
            data['projects'][parent_project.name] = parent_project
            return parent_project

        project.get_streak_status()
        self._store_project_entity(data, project)
        return project

    def share_project_progress(self, project: en.Project):
        """Копирует картинку прогресса проекта в буфер обмена."""
        if project.goal == float('inf'):
            self.notifications.show_warning("Для проекта без цели нельзя создать картинку прогресса")
            return

        image = self._create_progress_share_image(project)
        QApplication.clipboard().setImage(image)
        self.notifications.show_info("Картинка прогресса добавлена в буфер обмена")

    def _create_progress_share_image(self, project: en.Project) -> QImage:
        size = 1080
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(QColor("#FFFFFF"))

        progress = max(0, min(100, int(round(project.progress))))
        center = size / 2
        ring_outer = 620
        ring_width = 78
        ring_rect = QRectF(
            center - ring_outer / 2,
            125,
            ring_outer,
            ring_outer
        )

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        progress_color = self._get_progress_share_color(progress)

        pen = QPen(QColor("#E6EBEF"))
        pen.setWidth(ring_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(ring_rect, 0, 360 * 16)

        if progress > 0:
            pen.setColor(progress_color)
            painter.setPen(pen)
            painter.drawArc(ring_rect, 90 * 16, int(-progress * 360 * 16 / 100))

        percent_font = self._make_progress_share_font(210, bold=True)
        painter.setFont(percent_font)
        painter.setPen(progress_color)
        painter.drawText(ring_rect, Qt.AlignCenter, f"{progress}%")

        title_area = QRectF(80, 805, size - 160, 157)
        title_text = self._get_progress_share_title(project)
        title_font = self._make_progress_share_font(1, bold=True)
        title_font = self._fit_progress_share_font(
            title_text,
            title_area,
            title_font,
            max_pixel_size=self._get_progress_share_title_max_size(title_text),
            min_pixel_size=27
        )
        painter.setPen(QColor("#000000"))
        painter.setFont(title_font)
        title_rect = self._centered_progress_share_text_rect(title_text, title_area, title_font)
        painter.drawText(title_rect, Qt.AlignCenter | Qt.TextWordWrap, title_text)
        self._draw_progress_share_brand(painter, size)
        painter.end()
        return image

    def _get_progress_share_title(self, project: en.Project) -> str:
        if self._is_stage(project):
            parent_name = getattr(project, 'parent_project_name', None)
            if not parent_name:
                parent_project = self._get_parent_project(project)
                parent_name = parent_project.name if parent_project is not None else None
            if parent_name:
                return f"{parent_name}: {project.name}"
        return project.name

    def _make_progress_share_font(self, pixel_size: int, bold: bool = False) -> QFont:
        font = QFont("Arial")
        font.setPixelSize(pixel_size)
        font.setBold(bold)
        return font

    def _get_progress_share_title_max_size(self, title: str) -> int:
        length = len(title.strip())
        if length <= 1:
            return 155
        if length <= 4:
            return 139
        if length <= 14:
            return 123
        if length <= 28:
            return 104
        return 85

    def _fit_progress_share_font(
            self,
            text: str,
            rect: QRectF,
            font: QFont,
            max_pixel_size: int,
            min_pixel_size: int
    ) -> QFont:
        fitted_font = QFont(font)

        for pixel_size in range(max_pixel_size, min_pixel_size - 1, -2):
            fitted_font.setPixelSize(pixel_size)
            metrics = QFontMetrics(fitted_font)
            bounding = metrics.boundingRect(
                rect.toRect(),
                Qt.AlignCenter | Qt.TextWordWrap,
                text
            )
            if bounding.width() <= rect.width() and bounding.height() <= rect.height():
                return fitted_font

        fitted_font.setPixelSize(min_pixel_size)
        return fitted_font

    def _centered_progress_share_text_rect(self, text: str, area: QRectF, font: QFont) -> QRectF:
        metrics = QFontMetrics(font)
        bounding = metrics.boundingRect(
            area.toRect(),
            Qt.AlignCenter | Qt.TextWordWrap,
            text
        )
        text_height = min(bounding.height(), area.height())
        y = area.y() + (area.height() - text_height) / 2
        return QRectF(area.x(), y, area.width(), text_height)

    def _draw_progress_share_brand(self, painter: QPainter, image_size: int):
        icon_size = 46
        spacing = 14
        brand_text = "nfprogress"
        icon = self._load_progress_share_icon()

        brand_font = self._make_progress_share_font(37, bold=True)
        painter.setFont(brand_font)
        painter.setPen(QColor("#2568AC"))

        metrics = QFontMetrics(brand_font)
        text_width = metrics.horizontalAdvance(brand_text)
        text_height = metrics.height()
        group_width = icon_size + spacing + text_width if not icon.isNull() else text_width
        group_x = (image_size - group_width) / 2
        center_y = image_size - 54

        if not icon.isNull():
            icon_rect = QRectF(group_x, center_y - icon_size / 2, icon_size, icon_size)
            painter.drawImage(icon_rect, icon)
            text_x = group_x + icon_size + spacing
        else:
            text_x = group_x

        text_rect = QRectF(text_x, center_y - text_height / 2, text_width, text_height)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, brand_text)

    def _load_progress_share_icon(self) -> QImage:
        for path in self._progress_share_icon_candidates("Icon.svg"):
            icon = self._load_progress_share_icon_from_qicon(path)
            if not icon.isNull():
                return icon

        for path in self._progress_share_icon_candidates("icon.ico"):
            icon = self._load_progress_share_icon_from_qicon(path)
            if not icon.isNull():
                return icon

        return QImage()

    def _load_progress_share_icon_from_qicon(self, path: str) -> QImage:
        icon = QIcon(path)
        if icon.isNull():
            return QImage()

        pixmap = icon.pixmap(QSize(256, 256))
        if pixmap.isNull():
            return QImage()

        return pixmap.toImage()

    def _progress_share_icon_candidates(self, icon_file: str) -> list[str]:
        return [
            en.resource_path(icon_file),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), icon_file),
            os.path.join(os.getcwd(), icon_file),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), icon_file),
            os.path.join(os.path.dirname(os.path.abspath(sys.executable)), icon_file),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))),
                "Resources",
                icon_file
            ),
        ]

    def _get_progress_share_color(self, progress: int) -> QColor:
        ratio = max(0.0, min(1.0, progress / 100.0))
        start_color = QColor("#A9A9A9")
        end_color = QColor("#2568AC")

        r = start_color.red() + ratio * (end_color.red() - start_color.red())
        g = start_color.green() + ratio * (end_color.green() - start_color.green())
        b = start_color.blue() + ratio * (end_color.blue() - start_color.blue())

        return QColor(int(r), int(g), int(b))

    def load_notes(self, project):
        """Загружает список заметок проекта с отображением добавленного и общего количества."""
        # Сбрасываем выделение перед clear() — иначе нативная анимация смены
        # выделенного элемента может тикать на уже уничтоженном QListWidgetItem
        # (см. аналогичный фикс для list_projects в refresh_projects()).
        self.note_list.clearSelection()
        self.note_list.setCurrentItem(None)
        self.note_list.clear()

        # Получаем единицу измерения для отображения
        unit_code = project.unit

        # Проверяем и восстанавливаем прогресс для записей, где он отсутствует
        data_changed = False
        notes_with_stage_names = project.get_notes_with_stage_names()
        for _, note in notes_with_stage_names:
            # Если added_progress равно 0 или None, но added_symbols > 0, вычисляем прогресс
            if (note.get_added_progress() == 0 or note.get_added_progress() is None) and note.get_added_symbols() != 0:
                goal_symbols = project.get_goal_symbols()
                if goal_symbols != float('inf') and goal_symbols > 0:
                    # Вычисляем правильный прогресс
                    added_progress = (note.get_added_symbols() / goal_symbols * 100)

                    # Создаём новую заметку с исправленным прогрессом
                    fixed_note = en.Note(
                        note.get_new_total(),
                        note.get_added_symbols(),
                        added_progress,
                        note.date_create
                    )

                    # Заменяем заметку в списке
                    if project.has_stages():
                        for stage in project.stages:
                            if note in stage.notes:
                                index = stage.notes.index(note)
                                stage.notes[index] = fixed_note
                                break
                    else:
                        index = project.notes.index(note)
                        project.notes[index] = fixed_note
                    data_changed = True

        # Если были изменения, сохраняем данные
        if data_changed:
            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)

        # Отображаем заметки
        notes_to_show = notes_with_stage_names if project.has_stages() else notes_with_stage_names[-10:]
        for stage_name, note in reversed(notes_to_show):
            # Добавленное количество в единицах проекта
            added_disp = en.unit_converter('symbols', note.get_added_symbols(), project.unit)
            added_disp_str = self._format_number(added_disp)

            # Определяем знак изменения
            if added_disp > 0:
                sign = "+"
            elif added_disp < 0:
                sign = "-"
                added_disp_str = self._format_number(abs(added_disp))  # убираем минус для отображения
            else:
                sign = "±"  # на случай если 0 (хотя таких записей не должно быть)

            # Общее количество после записи в единицах проекта
            total_disp = en.unit_converter('symbols', note.get_new_total(), project.unit)
            total_disp_str = self._format_number(total_disp)

            # Прогресс в процентах
            progress_str = f"{note.get_added_progress():.2f}" if note.get_added_progress() else "0"

            # Определяем правильное склонение единицы измерения
            if unit_code == 'symbols':
                unit_display = self._pluralize_unit(total_disp, 'символ', 'символа', 'символов')
            elif unit_code == 'A4':
                unit_display = self._pluralize_unit(total_disp, 'лист', 'листа', 'листов')
            elif unit_code == 'author_list':
                unit_display = self._pluralize_unit(total_disp, 'авторский лист', 'авторских листа', 'авторских листов')
            elif unit_code == 'ficbook_pages':
                unit_display = self._pluralize_unit(total_disp, 'страница', 'страницы', 'страниц')
            else:
                unit_display = unit_code

            # Формируем строку: дата ±добавлено → общее (единица) [процент]
            stage_prefix = f"{stage_name}: " if stage_name else ""
            item_text = f"{stage_prefix}{note.get_date_create_str()} {sign}{added_disp_str} → {total_disp_str} {unit_display} ({progress_str}%)"

            item = QListWidgetItem(item_text)
            self.note_list.addItem(item)

    def _pluralize_unit(self, number, form1, form2, form5):
        """
        Возвращает правильную форму слова в зависимости от числа.
        form1 - для 1 (символ)
        form2 - для 2-4 (символа)
        form5 - для 5-20, 0 и больших чисел (символов)
        """
        number = int(number) if number == int(number) else int(number) + 1  # округляем вверх для нецелых

        if number % 10 == 1 and number % 100 != 11:
            return form1
        elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return form2
        else:
            return form5

    def add_note(self, project: en.Project):
        """Добавляет заметку к проекту."""
        text = self.new_symbols.text().strip()

        # Проверяем, что поле не пустое и содержит только цифры
        if not text:
            self.new_symbols.clear()
            self.notifications.show_error('Введите значение!')
            return

        try:
            if ',' in text:
                text = text.replace(',', '.')
            if project.unit != 'author_list':
                new_total_in_unit = math.ceil(float(text))
            else:
                new_total_in_unit = float(text)
        except ValueError:
            self.new_symbols.clear()
            self.notifications.show_error('Введите число!')
            return

        # Сохраняем старое значение для уведомления
        old_total_in_unit = project.total_units

        # Проверяем, изменилось ли количество
        if abs(new_total_in_unit - old_total_in_unit) < 0.01:
            self.notifications.show_info(
                "Значение не изменилось."
            )
            return

        # Конвертируем в символы для расчётов и сохранения в заметке
        new_total_symbols = en.unit_converter(project.unit, new_total_in_unit, 'symbols')
        current_total_symbols = project.get_total_symbols()
        added_symbols = new_total_symbols - current_total_symbols
        goal_symbols = project.get_goal_symbols()

        if goal_symbols == float('inf'):
            added_progress = 0
        else:
            added_progress = (added_symbols / goal_symbols * 100) if goal_symbols > 0 else 0

        # Создаём заметку (храним new_total в символах)
        note = en.Note(new_total_symbols, added_symbols, added_progress)

        # Обновляем проект (total_units обновится в единице проекта через set_new_notes)
        project.set_new_notes(note)

        # Загружаем данные
        data = en.load_data()
        self._store_project_entity(data, project)
        bonus_project = self._get_streak_bonus_project(data, project)
        settings = en.load_settings()

        # Обновляем игровой режим ТОЛЬКО если символы были ДОБАВЛЕНЫ (не удалены)
        if settings.get('game_mode', False) and added_symbols > 0:
            self.game_controller.add_symbols(added_symbols)
            # Даем бонус за стрик проекта и глобальный, если он включен
            if settings.get('global_streak', False):
                if bonus_project.last_streak_bonus != en.today_for_test():
                    if self.game_controller.give_streak_bonus(bonus_project.get_streak_status(), 'Local', en.streak_length(bonus_project.streaks)):
                        bonus_project.last_streak_bonus = en.today_for_test()
                        self._store_project_entity(data, bonus_project)
                # Даем бонус за глобальный стрик
                if data.get('last_global_streak_bonus', None) != en.today_for_test():
                    if self.game_controller.give_streak_bonus(self._get_global_streak_status_after_auto_freeze(data), 'Global', len(data['global_streaks'])):
                        data['last_global_streak_bonus'] = en.today_for_test()

        # Сохраняем изменения
        self._store_project_entity(data, project)
        en.save_data(data)

        if settings.get('global_streak', False):
            # Обновляем глобальный стрик
            self.refresh_global_streak_status()

        # Обновляем состояние кнопок, если цель достигнута
        if project.total_units >= project.goal:
            self.setup_project_buttons(project)

        # Очищаем поле ввода
        self.new_symbols.clear()

        # Обновляем текущий виджет в списке
        if self._is_stage(project):
            parent_project = self._get_parent_project(project)
            if parent_project is not None:
                self._expanded_stage_projects.add(parent_project.name)
                self._update_project_list_widgets_for_stage(parent_project, project.stage_id)
                self.select_stage_by_id(parent_project.name, project.stage_id)
        else:
            current_item = self.list_projects.currentItem()
            if current_item:
                widget = self.list_projects.itemWidget(current_item)
                if widget:
                    widget.update_display()

        # Обновляем панель информации и список заметок
        self.show_project_info(project)
        self.load_notes(project)

        # Обновляем написанное сегодня во всех проектах
        self.written_today_in_all_projects()

        added_in_unit = new_total_in_unit - old_total_in_unit
        abs_added = abs(added_in_unit)

        # Определяем правильное склонение единицы измерения
        unit_display = self._get_unit_display(project.unit, abs_added)

        # Формируем сообщение в зависимости от знака изменения
        if added_in_unit > 0:
            self.notifications.show_success(
                f'В проект добавлено {self._format_number(abs_added)} {unit_display}',
                position="bottom-right"
            )
        elif added_in_unit < 0:
            self.notifications.show_warning(
                f'Из проекта удалено {self._format_number(abs_added)} {unit_display}',
                position="bottom-right"
            )

    def delete_selected_note(self, project):
        """Удаляет выбранную заметку из проекта."""
        current_item = self.note_list.currentItem()

        if current_item is None:
            self.notifications.show_warning('Выберите запись для удаления!')
            return

        selected_row = self.note_list.currentRow()

        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите удалить эту запись?\nЭто действие нельзя отменить!')
        result = dialog.exec()

        if result == QDialog.Accepted:
            # Находим индекс заметки в оригинальном списке (с учётом реверса)
            note_index = len(project.notes) - 1 - selected_row

            # Удаляем заметку
            deleted_note = project.notes.pop(note_index)

            # Обновляем total_units, беря последнюю запись
            if project.notes:
                last_note = project.notes[-1]
                # last_note.new_total в символах, конвертируем в единицу проекта
                project.total_units = en.unit_converter('symbols', last_note.new_total, project.unit)
            else:
                project.total_units = 0

            # Сохраняем изменения
            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)

            # Обновляем отображение
            parent_for_stage = self._get_parent_project(project) if self._is_stage(project) else None
            if parent_for_stage is not None:
                self._expanded_stage_projects.add(parent_for_stage.name)
            self.refresh_projects()
            if parent_for_stage is not None:
                self.select_stage_by_id(parent_for_stage.name, project.stage_id)
            else:
                self.select_project_by_name(project.name)
            self.show_project_info(project)
            self.load_notes(project)

            self.notifications.show_success('Запись удалена')

    def edit_project(self, project):
        """Редактирует существующий проект."""
        data = en.load_data()
        if self._is_stage(project):
            parent, _ = self._find_stage_parent(data, project)
            existing_names = [stage.name for stage in parent.stages] if parent else []
        else:
            existing_names = data['projects'].keys()
        dialog = EditProject(project, existing_names=existing_names)
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()
            old_name = project.name
            old_goal = project.goal
            old_total = project.total_units
            old_deadline = project.deadline
            old_personal_goal = project.personal_goal_for_the_day
            parent_with_stages = not self._is_stage(project) and project.has_stages()

            # Получаем новые значения из диалога
            new_name = dialog.get_name()
            new_goal = dialog.get_goal()
            new_total = dialog.get_total()
            new_unit = dialog.get_unit()
            if new_unit != 'author_list':
                new_goal = math.ceil(new_goal)
                new_total = math.ceil(new_total)
            new_deadline = dialog.get_deadline()
            new_personal_goal = dialog.get_personal_goal_for_the_day()
            stages_enabled = dialog.is_stages_enabled()
            if parent_with_stages:
                new_goal = old_goal
                new_total = old_total
            if [old_name != new_name, old_goal != new_goal, old_total != new_total, old_deadline != new_deadline]:
                edit_date = en.today_for_test()

            # Проверяем, изменилась ли единица измерения
            unit_changed = (new_unit != project.unit)

            settings = en.load_settings()

            # Предупреждаем, что уменьшить цель на день не выйдет
            if old_personal_goal < new_personal_goal and settings.get('global_streak', False) and not en.dev_mode:
                if not en.streak_contains_day(project.streaks, en.today_for_test()):
                    # 1. Создаем диалог
                    confirm_goal_dialog = ConfirmDialog()

                    # 2. НАСТРАИВАЕМ текст (ДО вызова exec)
                    confirm_goal_dialog.message.setText(
                        'Вы хотите увеличить цель на день, уменьшить ее не выйдет, пока она не будет выполнена.'
                        '\nПродолжить?')

                    # 3. Показываем диалог и ждем решения пользователя
                    result_personal_goal = confirm_goal_dialog.exec()

                    # 4. Обрабатываем результат
                    if result_personal_goal == QDialog.Accepted:
                        project.personal_goal_for_the_day = new_personal_goal

            # Если персональная цель проекта изменилась и сегодня есть в стриках - удаляем сегодняшнюю дату
            if old_personal_goal < new_personal_goal and project.streaks and settings.get('global_streak', False):
                if en.streak_last_day(project.streaks) == en.today_for_test():
                    # 1. Создаем диалог
                    confirm_goal_dialog = ConfirmDialog()

                    # 2. НАСТРАИВАЕМ текст (ДО вызова exec)

                    if settings.get('game_mode') and settings.get('global_streak'):
                        confirm_goal_dialog.message.setText(
                            'Вы увеличиваете цель на день в проекте, где стрик уже продлен, если вы сохраните изменения, вам придется продлить стрик заново. Нового бонуса за стрик не будет.'
                            '\nУменьшить цель не получится, пока вы ее не выполните!'
                            '\nПродолжить?'
                        )
                    elif settings.get('global_streak'):  # ВАЖНО: используем elif, чтобы не перезаписать текст
                        confirm_goal_dialog.message.setText(
                            'Вы увеличиваете цель на день в проекте, где стрик уже продлен, если вы сохраните изменения, вам придется продлить стрик заново.'
                            '\nУменьшить цель не получится, пока вы ее не выполните!'
                            '\nПродолжить?')

                    # 3. Показываем диалог и ждем решения пользователя
                    result_personal_goal = confirm_goal_dialog.exec()

                    # 4. Обрабатываем результат
                    if result_personal_goal == QDialog.Accepted:
                        en.remove_streak_day(project.streaks, en.today_for_test())
                    else:
                        return
            # Запрещаем менять цель на день, если стрик не продлен сегодня
            if old_personal_goal > new_personal_goal and not en.dev_mode:
                if project.streaks and not en.streak_contains_day(project.streaks, en.today_for_test()) and not dialog.checkBox.isChecked():
                    # 1. Создаем диалог
                    confirm_goal_dialog = ConfirmDialog()

                    # 2. НАСТРАИВАЕМ текст (ДО вызова exec)
                    confirm_goal_dialog.message.setText(
                            'Нельзя уменьшить цель на день, пока не выполнена текущая.')

                    # 3. Показываем диалог и ждем решения пользователя
                    result_personal_goal = confirm_goal_dialog.exec()

                    # 4. Обрабатываем результат
                    if result_personal_goal == QDialog.Accepted:
                        return
            # Если удаляем дедлайн с активным стриком
            if dialog.checkBox.isChecked() and project.streaks:
                # 1. Создаем диалог
                confirm_goal_dialog = ConfirmDialog()

                # 2. НАСТРАИВАЕМ текст (ДО вызова exec)
                if not self._is_stage(project) and project.has_stages():
                    confirm_goal_dialog.message.setText(
                        'Если вы удалите дедлайн проекта, стрик проекта будет потерян.\n'
                        'Этапы снова будут вести собственные стрики по своим дедлайнам и текущей активности.\n'
                        'Ранее перенесенный в проект стрик не вернется этапам как история.\n'
                        'Продолжить?'
                    )
                else:
                    confirm_goal_dialog.message.setText(
                        'Если вы удалите дедлайн, стрик проекта будет потерян!\n'
                        'Продолжить?'
                    )

                # 3. Показываем диалог и ждем решения пользователя
                result_personal_goal = confirm_goal_dialog.exec()

                # 4. Обрабатываем результат
                if result_personal_goal == QDialog.Accepted:
                    project.streaks.clear()
                else:
                    return

            if (
                    not self._is_stage(project)
                    and project.has_stages()
                    and old_deadline == 'Нет'
                    and new_deadline != 'Нет'
                    and any(en.streak_length(stage.streaks) > 0 for stage in project.stages)
            ):
                confirm_goal_dialog = ConfirmDialog()
                confirm_goal_dialog.message.setText(
                    'При добавлении дедлайна проекта самый длинный стрик этапа будет перенесен в проект.\n'
                    'Стрики этапов будут очищены и начнутся заново. Дедлайны этапов сохранятся.\n'
                    'Продолжить?'
                )
                if confirm_goal_dialog.exec() != QDialog.Accepted:
                    return


            # Если единица изменилась, показываем предупреждение
            if unit_changed:
                confirm_dialog = ConfirmDialog()
                confirm_dialog.message.setText(
                    'Изменение типа отслеживаемого значения приведет к необратимой конвертации текущей цели, прогресса и записей в новый тип (с округлением в большую сторону).\nПродолжить?'
                )
                if confirm_dialog.exec() != QDialog.Accepted:
                    return  # Отменяем сохранение, если пользователь не согласен

            # Если имя изменилось у верхнеуровневого проекта, удаляем старую запись
            if not self._is_stage(project) and old_name != new_name and old_name in data['projects']:
                del data['projects'][old_name]

            # Обновляем поля проекта
            if unit_changed and not self._is_stage(project) and project.has_stages():
                for stage in project.stages:
                    stage.goal = en.unit_converter(project.unit, stage.goal, new_unit)
                    stage.total_units = en.unit_converter(project.unit, stage.total_units, new_unit)
                    stage.unit = new_unit
            project.name = new_name
            if not parent_with_stages:
                project.goal = new_goal
                project.total_units = new_total
            project.unit = new_unit
            project.deadline = new_deadline
            project.personal_goal_for_the_day = new_personal_goal
            project.edit_date = edit_date
            if not self._is_stage(project):
                if stages_enabled and not project.has_stages():
                    project.convert_to_stages()
                elif not stages_enabled and project.has_stages():
                    project.convert_to_single()
                if project.has_stages():
                    for stage in project.stages:
                        stage.parent_project_name = project.name
                    for stage in dialog.get_pending_stages():
                        stage.parent_project_name = project.name
                        stage.unit = project.unit
                        project.stages.append(stage)

            # Обновляем статус проекта (если цель достигнута)
            if project.total_units >= project.goal and project.status != 'завершен':
                # Не завершаем автоматически, но обновим кнопки позже
                pass

            # Обновляем цель на день
            project.get_today_goal_value()
            # Сохраняем под новым именем (или старым, если не изменилось)
            self._store_project_entity(data, project)
            en.save_data(data)

            # Обновляем интерфейс
            parent_for_stage = self._get_parent_project(project) if self._is_stage(project) else None
            if parent_for_stage is not None:
                self._expanded_stage_projects.add(parent_for_stage.name)
            self.refresh_projects()
            self.refresh_global_streak_status()
            if self._is_stage(project) and parent_for_stage is not None:
                self.select_stage_by_id(parent_for_stage.name, project.stage_id)
            else:
                self.select_project_by_name(project.name)
            self.name_selected_project.setText(project.name)
            self.view_project()

            unit_name = self._get_unit_name(project.unit)
            entity_label = "Этап" if self._is_stage(project) else "Проект"
            self.notifications.show_success(
                f'{entity_label} "{project.name}" обновлён',
                position="bottom-left"
            )

    def developer_mode(self):
        dialog = DeveloperMode()
        result = dialog.exec_()
        settings = load_settings()
        test_date_enabled = dialog.test_date_cb.isChecked()
        if result == QDialog.Accepted:
            selected_test_datetime = dialog.get_today_for_test()
            # Сохраняем данные персонажа
            self.game_controller.gamer.level = int(dialog.level.text())
            self.game_controller.gamer.update_max_health()
            health = round(float(dialog.health.text().replace(',', '.')), 1)
            self.game_controller.gamer.health = max(0, min(self.game_controller.gamer.get_max_health(), health))
            self.game_controller.gamer.coins = self.game_controller.gamer.round_money(dialog.coins.text())
            self.game_controller.gamer.exp = int(float(dialog.exp.text()))
            self.game_controller.gamer.update_cf()
            self.game_controller.gamer.calculate_inflation()
            self.game_controller.gamer.save()
            # Сохраняем статус даты для теста и ее
            settings['today_for_test_mode'] = test_date_enabled
            settings['today_for_test_datetime'] = selected_test_datetime
            settings['today_for_test_date'] = selected_test_datetime.date() if selected_test_datetime else None
            save_settings(settings)
            self._last_effective_date = en.today_for_test()

            # Выводим уведомление и обновляем проекты с глобальным стриком
            self.notifications.show_success('Изменения сохранены')
            self.refresh_projects()
            self.refresh_global_streak_status()
            self.game_controller.refresh_all()
        dialog.close()

    def _get_unit_name(self, unit_code):
        """Возвращает название единицы по коду."""
        units = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }
        return units.get(unit_code, unit_code)

    def complete_project(self, project):
        """Завершает проект"""
        dialog = ConfirmDialog()
        entity_label = 'этап' if self._is_stage(project) else 'проект'
        dialog.message.setText(
            f'Вы хотите завершить {entity_label}?\nЭто действие нельзя отменить\n'
            f'Завершенный {entity_label} можно только просматривать и удалить')
        result = dialog.exec()

        if result == QDialog.Accepted:
            project.status = "завершен"
            project.complete_date = en.today_for_test()
            if en.load_settings()['game_mode'] and not self._is_stage(project):
                self.game_controller.give_complete_bonus(project.status, project.total_units, project.unit)
                if en.load_settings()['global_streak'] and project.deadline != 'Нет' and en.streak_length(project.streaks):
                    self.game_controller.give_streak_bonus(streak_status='Complete', streak_type='Local', streak_len=en.streak_length(project.streaks))

            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.notifications.show_success(f'{project.name} завершен!')

    def archive_project(self, project):
        """Отправляет проект в архив или активирует его"""
        if self._is_stage(project):
            self.notifications.show_warning("Этапы нельзя отправить в архив")
            return

        dialog = ConfirmDialog()

        if project.status == 'активен':
            dialog.message.setText(
                'Вы хотите архивировать проект?\nДедлайн проекта будет удален, стрик прерван.\nпроект можно будет восстановить')
        else:
            dialog.message.setText('Вы хотите активировать проект?')

        result = dialog.exec()

        if result == QDialog.Accepted:
            if project.status == 'активен':
                project.status = "в архиве"
                project.deadline = 'Нет'
                project.streaks = []
                project.streak_status = 'No'
                msg = f'{project.name} архивирован.'
            else:
                project.status = "активен"
                msg = f'{project.name} снова активен.'
                # При активации дедлайн остается пустым, пользователь может установить его позже

            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.notifications.show_success(msg, position="bottom-left")

    def delete_project(self, project):
        """Удаляет проект"""
        dialog = ConfirmDialog()
        entity_label = 'этап' if self._is_stage(project) else 'проект'
        dialog.message.setText(f'Вы хотите удалить {entity_label}?\nЭто действие нельзя отменить!')
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()
            if self._is_stage(project):
                parent, index = self._find_stage_parent(data, project)
                if parent is not None:
                    deleted_name = parent.stages[index].name
                    del parent.stages[index]
                    if not parent.stages:
                        parent.enable_stages = False
                    data['projects'][parent.name] = parent
                    en.save_data(data)
                    self.notifications.show_success(f'{deleted_name} удален.', position="bottom-left")
            elif project.name in data['projects']:
                del data['projects'][project.name]
                en.save_data(data)
                self.notifications.show_success(f'{project.name} удален.', position="bottom-left")

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)

    def _is_stage(self, project):
        return isinstance(project, en.Stage) or getattr(project, 'is_stage', False)

    def _find_stage_parent(self, data, stage):
        stage_id = getattr(stage, 'stage_id', None)
        parent_name = getattr(stage, 'parent_project_name', None)
        projects = data.get('projects', {})

        candidates = []
        if parent_name and parent_name in projects:
            candidates.append(projects[parent_name])
        candidates.extend(project for name, project in projects.items() if name != parent_name)

        for parent in candidates:
            if not getattr(parent, 'has_stages', lambda: False)():
                continue
            for index, current_stage in enumerate(parent.stages):
                if stage_id and getattr(current_stage, 'stage_id', None) == stage_id:
                    return parent, index
                if not stage_id and current_stage.name == stage.name:
                    return parent, index
        return None, None

    def _store_project_entity(self, data, project):
        if self._is_stage(project):
            parent, index = self._find_stage_parent(data, project)
            if parent is None:
                return False
            project.parent_project_name = parent.name
            parent.stages[index] = project
            data['projects'][parent.name] = parent
            return True

        data['projects'][project.name] = project
        if getattr(project, 'has_stages', lambda: False)():
            for stage in project.stages:
                stage.parent_project_name = project.name
        return True

    def _get_parent_project(self, project):
        if not self._is_stage(project):
            return project
        data = en.load_data()
        parent, _ = self._find_stage_parent(data, project)
        return parent

    def _toggle_project_stages(self, project_name):
        scroll_bar = self.list_projects.verticalScrollBar()
        scroll_value = scroll_bar.value()
        expanding = project_name not in self._expanded_stage_projects
        if project_name in self._expanded_stage_projects:
            self._expanded_stage_projects.remove(project_name)
        else:
            self._expanded_stage_projects.add(project_name)
        self.refresh_projects(preserve_scroll=True, scroll_value=scroll_value)
        self.select_project_by_name(project_name)
        if expanding:
            QTimer.singleShot(0, lambda name=project_name: self._scroll_to_first_stage(name))

    def _scroll_to_first_stage(self, parent_project_name):
        for i in range(self.list_projects.count()):
            item = self.list_projects.item(i)
            widget = self.list_projects.itemWidget(item)
            if (
                    widget is not None
                    and self._is_stage(getattr(widget, 'project', None))
                    and getattr(widget.project, 'parent_project_name', None) == parent_project_name
            ):
                self.list_projects.scrollToItem(item)
                return

    def _update_project_list_widgets_for_stage(self, parent_project, stage_id):
        """Обновляет виджеты родителя и этапа без пересоздания списка, чтобы сохранить анимацию."""
        for i in range(self.list_projects.count()):
            item = self.list_projects.item(i)
            widget = self.list_projects.itemWidget(item)
            if widget is None or not hasattr(widget, 'project'):
                continue

            if not self._is_stage(widget.project) and widget.project.name == parent_project.name:
                widget.project = parent_project
                widget.update_display()
                item.setSizeHint(widget.sizeHint())
            elif self._is_stage(widget.project) and getattr(widget.project, 'stage_id', None) == stage_id:
                stage = next(
                    (current_stage for current_stage in parent_project.stages
                     if getattr(current_stage, 'stage_id', None) == stage_id),
                    None
                )
                if stage is not None:
                    widget.project = stage
                    widget.parent_project = parent_project
                    widget.update_display()
                    item.setSizeHint(widget.sizeHint())

    def _sync_project_key(self, project):
        if self._is_stage(project):
            return f"{getattr(project, 'parent_project_name', '')}:{getattr(project, 'stage_id', project.name)}"
        return project.name

    def generate_project_widget(self, project):
        return ProjectWidget(
            project,
            en.load_settings()['global_streak'],
            expanded=project.name in self._expanded_stage_projects,
            toggle_callback=self._toggle_project_stages,
        )

    def on_filter_changed(self):
        """Обработчик изменения фильтра проектов"""
        settings = en.load_settings()
        settings['project_filter'] = self.filter_project_box.currentText()
        save_settings(settings)
        self.refresh_projects()

    def on_sort_changed(self):
        '''Обработчик изменения сортировки проектов'''
        settings = en.load_settings()
        settings['project_sort'] = self.sort_project_box.currentText()
        save_settings(settings)
        self.refresh_projects()

    def on_tab_changed(self, index):
        """Обработчик переключения вкладок"""
        current_tab = self.tabWidget.tabText(index)

        # Если текущая вкладка - "Проекты", обновляем список
        if current_tab == "Проекты":
            self.refresh_projects()
            self.refresh_global_streak_status()

            # Если есть выбранный проект, обновляем его информацию
            current_item = self.list_projects.currentItem()
            if current_item:
                widget = self.list_projects.itemWidget(current_item)
                if widget and hasattr(widget, 'project'):
                    self.show_project_info(widget.project)
                    self.setup_project_buttons(widget.project)

    def refresh_global_streak_status(self):
        # Загружаем глобальный стрик
        data = en.load_data()
        auto_freeze_changed = self._refresh_project_streak_statuses(data)
        if auto_freeze_changed:
            self._refresh_game_inventory()
        # Обновляем глобальный стрик на основе проектов
        global_status = en.global_streak_status(data)
        status_msg = en.global_streak_status_msg(data, global_status)
        self.global_streak_status.setText(status_msg if status_msg else "Глобальный стрик не начат")

    def _refresh_game_inventory(self):
        """Перезагружает игрока после фонового списания предметов."""
        if not getattr(self, 'game_controller', None):
            return

        self.game_controller.gamer = game.load_game()
        self.game_controller.update_inventory()
        self.game_controller.update_shops()
        self.game_controller.update_game_data()

    def _get_global_streak_status_after_auto_freeze(self, data):
        """Сначала применяет автозаморозки, потом считает глобальный стрик."""
        auto_freeze_changed = self._refresh_project_streak_statuses(data)
        if auto_freeze_changed:
            self._refresh_game_inventory()
        return en.global_streak_status(data)

    def _refresh_project_streak_statuses(self, data, show_auto_freeze_toasts=True):
        """Актуализирует локальные стрики и показывает уведомления об автозаморозках."""
        projects = data.get('projects', {})
        global_streaks = data.setdefault('global_streaks', [])
        if not isinstance(global_streaks, list):
            global_streaks = []
            data['global_streaks'] = global_streaks
        notifications = data.get('notifications', {'new': [], 'read': []})
        if not isinstance(notifications, dict):
            notifications = {'new': [], 'read': []}
        notifications.setdefault('new', [])
        notifications.setdefault('read', [])

        changed = False
        for project_name, project in projects.items():
            if not isinstance(project, en.Project):
                continue

            streak_sources = project.stages if project.has_stages() and project.deadline == 'Нет' else [project]
            project_freezes_before = getattr(project, 'freezes', 0)
            previous_batch = en.begin_project_freeze_batch(project) if project.has_stages() and project.deadline == 'Нет' else None
            try:
                for streak_source in streak_sources:
                    old_streaks = list(streak_source.streaks) if isinstance(streak_source.streaks, list) else []
                    old_freeze_count = sum(1 for entry in old_streaks if entry == en.STREAK_FREEZE_MARKER)
                    streak_source.get_streak_status()

                    freeze_days = [
                        effective_day
                        for entry, effective_day in en.iter_streak_days(streak_source.streaks)
                        if entry == en.STREAK_FREEZE_MARKER
                    ]
                    new_freeze_days = freeze_days[old_freeze_count:]
                    if new_freeze_days:
                        changed = True
                        days_text = ', '.join(day.strftime('%d.%m.%Y') for day in new_freeze_days)

                        source_label = 'этапа' if self._is_stage(streak_source) else 'проекта'
                        if len(new_freeze_days) == 1:
                            message = f'Стрик {source_label} "{streak_source.name}" автоматически заморожен за {days_text}.'
                        else:
                            message = f'Стрик {source_label} "{streak_source.name}" автоматически заморожен за дни: {days_text}.'

                        notifications['new'].append(en.Notification(message, tag='streak'))
                        if show_auto_freeze_toasts and self.notifications:
                            self.notifications.show_info(message, position='bottom-right')

                        for freeze_day in new_freeze_days:
                            if en.streak_last_day(global_streaks) == freeze_day - datetime.timedelta(days=1):
                                global_streaks.append(en.STREAK_FREEZE_MARKER)
                                data['global_streak_status'] = 'Freeze'
            finally:
                if previous_batch is not None or project.has_stages() and project.deadline == 'Нет':
                    en.end_project_freeze_batch(previous_batch)

            if getattr(project, 'freezes', 0) != project_freezes_before:
                changed = True

            data['projects'][project_name] = project

        if changed:
            data['notifications'] = notifications
            en.save_data(data)
        return changed

    def refresh_projects(self, preserve_scroll=False, scroll_value=None):
        data = en.load_data()
        auto_freeze_changed = self._refresh_project_streak_statuses(data)
        if auto_freeze_changed:
            self._refresh_game_inventory()
        projects = list(data['projects'].values())

        # Обнововляем глобальный стрик
        if en.load_settings()['global_streak']:
            global_status = en.global_streak_status(data)
            status_msg = en.global_streak_status_msg(data, global_status)
            self.global_streak_status.setText(status_msg if status_msg else "Глобальный стрик не начат")

        # Получаем выбранный фильтр
        current_sort = self.sort_project_box.currentText()
        current_filter = self.filter_project_box.currentText()

        # Фильтруем проекты по статусу
        if current_filter == "Активен":
            projects = [p for p in projects if p.status == "активен"]
        elif current_filter == "В архиве":
            projects = [p for p in projects if p.status == "в архиве"]
        elif current_filter == "Завершен":
            projects = [p for p in projects if p.status == "завершен"]
        # Сортируем проекты
        if current_sort == 'Название':
            projects = sorted(projects, key=lambda p: p.name)
        elif current_sort == 'Дедлайн':
            # Исправленная сортировка по дедлайну
            def get_deadline_key(project):
                if project.deadline == 'Нет' or project.deadline is None:
                    return datetime.date.max  # проекты без дедлайна в конец
                return project.deadline

            projects = sorted(projects, key=get_deadline_key)
        elif current_sort == 'Прогресс':
            projects = sorted(projects, key=lambda p: p.progress, reverse=True)

        list_p = self.list_projects
        if scroll_value is None:
            scroll_value = list_p.verticalScrollBar().value()

        # Сохраняем текущий выбранный проект (если есть)
        current_project_name = None
        current_stage_id = None
        current_item = self.list_projects.currentItem()
        if current_item:
            widget = self.list_projects.itemWidget(current_item)
            if widget and hasattr(widget, 'project'):
                if self._is_stage(widget.project):
                    current_stage_id = getattr(widget.project, 'stage_id', None)
                    current_project_name = getattr(widget.project, 'parent_project_name', None)
                else:
                    current_project_name = widget.project.name

        # Сбрасываем текущее выделение перед clear(): нативная (macOS) анимация
        # смены выделенного элемента продолжает тикать на уже уничтоженном
        # QListWidgetItem, если элемент удалить прямо во время её проигрывания —
        # это и есть настоящий источник "Called attribute on invalid object".
        list_p.clearSelection()
        list_p.setCurrentItem(None)

        # Останавливаем анимации круговых прогресс-баров у старых виджетов,
        # иначе после clear() они продолжают тикать на уже удалённых объектах
        for i in range(list_p.count()):
            old_widget = list_p.itemWidget(list_p.item(i))
            if old_widget is not None and hasattr(old_widget, 'stop_animations'):
                old_widget.stop_animations()

        list_p.clear()

        settings = en.load_settings()
        should_give_streak_bonus = settings.get('game_mode', False) and settings.get('global_streak', False)
        data_changed = False

        for project in projects:
            widget = self.generate_project_widget(project)

            # Даем бонус за стрик проекта и глобальный, если он включен
            if should_give_streak_bonus:
                streak_sources = project.stages if project.has_stages() and project.deadline == 'Нет' else [project]
                for streak_source in streak_sources:
                    if streak_source.last_streak_bonus != en.today_for_test():
                        if self.game_controller.give_streak_bonus(streak_source.get_streak_status(), 'Local',
                                                                  en.streak_length(streak_source.streaks)):
                            streak_source.last_streak_bonus = en.today_for_test()
                            data['projects'][project.name] = project
                            data_changed = True
                # Даем бонус за глобальный стрик
                if data.get('last_global_streak_bonus', None) != en.today_for_test():
                    if self.game_controller.give_streak_bonus(self._get_global_streak_status_after_auto_freeze(data), 'Global',
                                                              len(data['global_streaks'])):
                        data['last_global_streak_bonus'] = en.today_for_test()
                        data_changed = True

            # Принудительно обновляем layout, чтобы sizeHint был актуальным
            widget.layout().activate()
            widget.widget.layout().activate()
            size = widget.sizeHint()

            item = QListWidgetItem()
            item.setSizeHint(size)
            list_p.addItem(item)
            list_p.setItemWidget(item, widget)

            if current_project_name and project.name == current_project_name:
                list_p.setCurrentItem(item)

            if getattr(project, 'has_stages', lambda: False)() and project.name in self._expanded_stage_projects:
                for stage in project.stages:
                    stage_widget = StageRowWidget(stage, project, settings.get('global_streak', False))
                    stage_widget.layout().activate()
                    stage_item = QListWidgetItem()
                    stage_item.setSizeHint(stage_widget.sizeHint())
                    list_p.addItem(stage_item)
                    list_p.setItemWidget(stage_item, stage_widget)
                    if current_stage_id and getattr(stage, 'stage_id', None) == current_stage_id:
                        list_p.setCurrentItem(stage_item)

        # Если после фильтрации текущий проект не найден, скрываем панели информации
        if current_project_name and not list_p.currentItem():
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.name_selected_project.setText("Выберите проект")

        if current_project_name:
            if current_stage_id:
                self.select_stage_by_id(current_project_name, current_stage_id)
            else:
                self.select_project_by_name(current_project_name)
        # Показываем, сколько написано сегодня в символах
        self.written_today_in_all_projects()
        if data_changed:
            en.save_data(data)
        if preserve_scroll:
            QTimer.singleShot(0, lambda value=scroll_value: list_p.verticalScrollBar().setValue(value))

    def check_global_streak(self):
        """Проверяет глобальный стрик и показывает уведомление"""
        current_effective_date = en.today_for_test()
        if not hasattr(self, '_last_effective_date'):
            self._last_effective_date = current_effective_date

        if current_effective_date != self._last_effective_date:
            self._refresh_for_effective_date_change(current_effective_date, show_notification=True)
        elif en.load_settings().get('global_streak', False):
            self.refresh_global_streak_status()

        QTimer.singleShot(60_000, self.check_global_streak)

    def user_agreement(self):
        dialog = UserAgreement()
        result = dialog.exec()
        agree = dialog.agree_checkBox.isChecked()
        settings = load_settings()

        if result == QDialog.Accepted and agree:
            settings['user_agreement'] = True
            save_settings(settings)
            dialog.close()
        else:
            sys.exit(0)

    def check_user_agreement(self):
        settings = en.load_settings()
        user_agreement = settings.get('user_agreement', False)
        if not user_agreement:
            self.user_agreement()

    def sync_project(self, project, background_synch=False, batch_id=None):
        if getattr(project, 'has_stages', lambda: False)():
            stages_with_sync = [
                stage for stage in project.stages
                if stage.synch is not None and stage.status == 'активен'
            ]
            if not stages_with_sync:
                if not background_synch:
                    self.notifications.show_info("Сначала настройте синхронизацию у этапа.")
                return False

            if batch_id is None:
                batch_id = object()
                self._background_sync_batches[batch_id] = {
                    'queue': list(stages_with_sync),
                    'completed': 0,
                    'total': len(stages_with_sync),
                    'silent': background_synch,
                }
            self._start_next_background_sync_item(batch_id)
            return True

        # Если синхронизация не настроена
        if project.synch is None:
            if background_synch:
                # Фоновая синхронизация для ненастроенного проекта — игнорируем
                return
            else:
                # Показываем окно настройки
                dialog = SynchWindow(project, self)
                if dialog.exec() != QDialog.Accepted:
                    return
                # Сохраняем изменения
                data = en.load_data()
                self._store_project_entity(data, project)
                en.save_data(data)
                # После настройки запускаем синхронизацию
                self.sync_project(project)
                return

        # Обработка в зависимости от типа
        if isinstance(project.synch, dict):
            sync_type = project.synch.get('type')

            if sync_type == 'word':
                if not background_synch:
                    return self._sync_word(project)
                else:
                    return self._sync_word(project, True, batch_id=batch_id)
            elif sync_type == 'scrivener':
                if not background_synch:
                    return self._sync_scrivener(project)
                else:
                    return self._sync_scrivener(project, True, batch_id=batch_id)
            else:
                self.notifications.show_error("Неизвестный тип синхронизации")
                return False
        else:
            # Старый формат (строка) – считаем как word
            # Конвертируем на лету
            project.synch = {'type': 'word', 'path': project.synch}
            return self._sync_word(project)

        return False

    def _start_sync_read(self, project, sync_type, background_synch=False, batch_id=None):
        project_name = self._sync_project_key(project)
        if project_name in self._sync_threads:
            if not background_synch:
                self.notifications.show_info("Синхронизация уже выполняется.")
            return False

        thread = QThread(self)
        worker = SyncReadWorker(project, sync_type, background_synch, batch_id)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_sync_read_finished)
        worker.failed.connect(self._on_sync_read_failed)

        self._sync_threads[project_name] = (thread, worker)
        thread.start()
        return True

    def _cleanup_sync_read_worker(self, project_name):
        thread_worker = self._sync_threads.pop(project_name, None)
        if thread_worker is None:
            return

        thread, worker = thread_worker
        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()

    def _start_next_background_sync_item(self, batch_id):
        if batch_id is None:
            return

        batch = self._background_sync_batches.get(batch_id)
        if batch is None:
            return

        while batch['queue']:
            project = batch['queue'].pop(0)
            if self.sync_project(project, True, batch_id=batch_id):
                return
            batch['completed'] += 1

        self._background_sync_batches.pop(batch_id, None)
        if not batch['silent']:
            self.notifications.show_success(f"Синхронизировано проектов: {batch['completed']}")

    def _finish_background_sync_item(self, batch_id):
        if batch_id is None:
            return

        batch = self._background_sync_batches.get(batch_id)
        if batch is None:
            return

        batch['completed'] += 1
        self._start_next_background_sync_item(batch_id)

    @Slot(object, str, object, object, object, bool, object)
    def _on_sync_read_finished(self, project, sync_type, symbols, note_date, read_error, background_synch, batch_id):
        self._cleanup_sync_read_worker(self._sync_project_key(project))

        if sync_type == 'word':
            self._handle_word_sync_read_result(project, symbols, note_date, read_error, background_synch)
        elif sync_type == 'scrivener':
            self._handle_scrivener_sync_read_result(project, symbols, note_date, read_error, background_synch)
        elif not background_synch:
            self.notifications.show_error("Неизвестный тип синхронизации")

        self._finish_background_sync_item(batch_id)

    @Slot(object, str, str, bool, object)
    def _on_sync_read_failed(self, project, sync_type, error, background_synch, batch_id):
        self._cleanup_sync_read_worker(self._sync_project_key(project))

        if not background_synch:
            if sync_type == 'word':
                self.notifications.show_error(f"Ошибка при чтении файла: {error}")
            elif sync_type == 'scrivener':
                self.notifications.show_error(f"Ошибка при синхронизации Scrivener: {error}")
            else:
                self.notifications.show_error(f"Ошибка синхронизации: {error}")

        self._finish_background_sync_item(batch_id)

    def _sync_word(self, project, background_synch=False, batch_id=None):
        """Синхронизация с Word-файлом"""
        return self._start_sync_read(project, 'word', background_synch, batch_id)

    def _handle_word_sync_read_result(self, project, symbols, note_date, read_error, background_synch=False):
        if read_error == 'missing':
            if not background_synch:
                self.notifications.show_error(
                    "Файл не найден. Возможно, он был перемещён.\n"
                    "Настройте синхронизацию заново."
                )
            project.synch = None
            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)
            return
        elif read_error == 'doc_unsupported':
            if not background_synch:
                self.notifications.show_error(
                    "Поддержка .doc временно недоступна.\n"
                    "Пожалуйста, сохраните файл как .docx."
                )
            return
        elif read_error == 'unsupported_format':
            if not background_synch:
                self.notifications.show_error("Неподдерживаемый формат файла.")
            return

        try:
            self._apply_sync_read_result(project, symbols, note_date, background_synch, "Синхронизация завершена")
        except Exception as e:
            if not background_synch:
                self.notifications.show_error(f"Ошибка при чтении файла: {str(e)}")

    def _apply_sync_read_result(self, project, symbols, note_date, background_synch, success_title):
        # Конвертируем количество символов в единицу проекта
        new_total_in_unit = en.unit_converter('symbols', symbols, project.unit)
        current_total_in_unit = project.total_units

        # Проверяем, изменилось ли количество
        if abs(new_total_in_unit - current_total_in_unit) < 0.01:  # допускаем погрешность округления
            if not background_synch:
                self.notifications.show_info(
                    "Количество символов не изменилось."
                )
            return

        # Вычисляем изменение
        added_in_unit = new_total_in_unit - current_total_in_unit
        added_symbols = en.unit_converter(project.unit, added_in_unit, 'symbols')
        new_total_symbols = project.get_total_symbols() + added_symbols

        # Вычисляем прогресс (для уведомления используем абсолютное значение)
        goal_symbols = project.get_goal_symbols()
        if goal_symbols == float('inf'):
            added_progress = 0
        else:
            added_progress = (abs(added_symbols) / goal_symbols * 100) if goal_symbols > 0 else 0

        # Создаём заметку (added_symbols может быть отрицательным)
        note = en.Note(new_total_symbols, added_symbols, added_progress, date_create=note_date)
        project.set_new_notes(note)

        # Обновляем информацию о проекте
        self.load_notes(project)
        self.show_project_info(project)

        # Обновляем написанное сегодня во всех проектах
        self.written_today_in_all_projects()

        # Обновляем дату последней синхронизации
        project.last_synch = datetime.datetime.now()  # используем текущее время

        # Обновляем статус в интерфейсе
        self.update_sync_status_label(project)

        data = en.load_data()
        self._store_project_entity(data, project)
        bonus_project = self._get_streak_bonus_project(data, project)
        settings = en.load_settings()

        # Обновляем игровой режим ТОЛЬКО если символы были ДОБАВЛЕНЫ (не удалены)
        if settings.get('game_mode', False) and added_symbols > 0:
            self.game_controller.add_symbols(added_symbols)
            # Даем бонус за стрик проекта и глобальный, если он включен
            if settings.get('global_streak', False):
                if bonus_project.last_streak_bonus != en.today_for_test():
                    if self.game_controller.give_streak_bonus(bonus_project.get_streak_status(), 'Local',
                                                              en.streak_length(bonus_project.streaks)):
                        bonus_project.last_streak_bonus = en.today_for_test()
                        self._store_project_entity(data, bonus_project)
                # Даем бонус за глобальный стрик
                if data.get('last_global_streak_bonus', None) != en.today_for_test():
                    if self.game_controller.give_streak_bonus(self._get_global_streak_status_after_auto_freeze(data), 'Global',
                                                              len(data['global_streaks'])):
                        data['last_global_streak_bonus'] = en.today_for_test()

        # Сохраняем изменения
        self._store_project_entity(data, project)
        en.save_data(data)

        # Обновляем глобальный стрик
        if settings.get('global_streak', False):
            self.refresh_global_streak_status()

        # Обновляем виджет проекта в списке (для анимации)
        if self._is_stage(project):
            parent_project = self._get_parent_project(project)
            if parent_project is not None:
                self._expanded_stage_projects.add(parent_project.name)
                self._update_project_list_widgets_for_stage(parent_project, project.stage_id)
                self.select_stage_by_id(parent_project.name, project.stage_id)
        else:
            current_item = self.list_projects.currentItem()
            if current_item and current_item is not None:
                widget = self.list_projects.itemWidget(current_item)
                if widget and hasattr(widget, 'project') and widget.project.name == project.name:
                    # Обновляем существующий виджет
                    widget.update_display()
                    self.written_today_in_all_projects()
                else:
                    # Если текущий виджет не соответствует проекту, ищем нужный
                    self.refresh_projects()
                    self.select_project_by_name(project.name)
            else:
                # Если ничего не выбрано, просто обновляем список
                self.refresh_projects()
                self.select_project_by_name(project.name)

        # Определяем правильное склонение единицы измерения для количества added_in_unit
        abs_added = abs(added_in_unit)
        unit_display = self._get_unit_display(project.unit, abs_added)

        # Формируем сообщение в зависимости от знака изменения
        if added_in_unit > 0:
            if not background_synch:
                self.notifications.show_success(
                    f"{success_title}.\n"
                    f"Добавлено {self._format_number(abs_added)} {unit_display}",
                    position="bottom-right"
                )
        else:
            if not background_synch:
                self.notifications.show_warning(
                    f"{success_title}.\n"
                    f"Удалено {self._format_number(abs_added)} {unit_display}",
                    position="bottom-right"
                )

    def _sync_scrivener(self, project, background_synch=False, batch_id=None):
        """Синхронизация с проектом Scrivener"""
        return self._start_sync_read(project, 'scrivener', background_synch, batch_id)

    def _handle_scrivener_sync_read_result(self, project, symbols, note_date, read_error, background_synch=False):
        if read_error == 'missing':
            if not background_synch:
                self.notifications.show_error(
                    "Папка проекта Scrivener не найдена.\n"
                    "Настройте синхронизацию заново."
                )
            project.synch = None
            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)
            return

        try:
            if symbols == 0 and project.total_units == 0:
                if not background_synch:
                    self.notifications.show_warning(
                        "Не удалось подсчитать символы. Возможно, документ пуст."
                    )
                return

            self._apply_sync_read_result(
                project,
                symbols,
                note_date,
                background_synch,
                "Синхронизация Scrivener завершена"
            )
        except Exception as e:
            if not background_synch:
                self.notifications.show_error(f"Ошибка при синхронизации Scrivener: {str(e)}")

    def _get_unit_display(self, unit_code, number):
        """
        Возвращает правильное склонение единицы измерения для указанного числа.
        """
        if unit_code == 'symbols':
            return self._pluralize_unit(number, 'символ', 'символа', 'символов')
        elif unit_code == 'A4':
            return self._pluralize_unit(number, 'лист', 'листа', 'листов')
        elif unit_code == 'author_list':
            return self._pluralize_unit(number, 'авторский лист', 'авторских листа', 'авторских листов')
        elif unit_code == 'ficbook_pages':
            return self._pluralize_unit(number, 'страница', 'страницы', 'страниц')
        else:
            return unit_code  # на всякий случай

    def get_current_project(self):
        """Возвращает объект Project для текущего выбранного элемента в списке или None."""
        current_item = self.list_projects.currentItem()
        if current_item:
            widget = self.list_projects.itemWidget(current_item)
            if widget and hasattr(widget, 'project'):
                return widget.project
        return None

    def on_sync_menu_triggered(self):
        """Обработчик меню 'Синхронизация'."""
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Нет выбранного проекта")
            return
        self.sync_project(project)

    def on_delete_sync_menu_triggered(self):
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Нет выбранного проекта")
            return
        has_stage_sync = (
                getattr(project, 'has_stages', lambda: False)() and
                any(stage.synch is not None for stage in project.stages)
        )
        if project.synch is None and not has_stage_sync:
            self.notifications.show_info("У этого проекта нет привязанной синхронизации")
            return

        dialog = ConfirmDialog()
        if has_stage_sync:
            dialog.message.setText("Вы действительно хотите удалить настройки синхронизации у всех этапов?")
        else:
            dialog.message.setText("Вы действительно хотите удалить настройки синхронизации?")
        if dialog.exec() == QDialog.Accepted:
            if has_stage_sync:
                for stage in project.stages:
                    stage.synch = None
                    stage.last_synch = None
            else:
                project.synch = None
                project.last_synch = None
            data = en.load_data()
            self._store_project_entity(data, project)
            en.save_data(data)
            self.notifications.show_success("Синхронизация отключена")
            self.refresh_projects()
            if self._is_stage(project):
                parent = self._get_parent_project(project)
                if parent is not None:
                    self.select_stage_by_id(parent.name, project.stage_id)
            else:
                self.select_project_by_name(project.name)

    def on_change_project_menu_triggered(self):
        """Обработчик меню 'Изменить проект'."""
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Нет выбранного проекта")
            return
        self.edit_project(project)

    def on_delete_project_menu_triggered(self):
        """Обработчик меню 'Удалить проект'."""
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Нет выбранного проекта")
            return

        dialog = ConfirmDialog()
        entity_label = "этап" if self._is_stage(project) else "проект"
        dialog.message.setText(
            f"Вы действительно хотите удалить {entity_label}?\n"
            "Это действие нельзя отменить!"
        )
        if dialog.exec() == QDialog.Accepted:
            data = en.load_data()
            if self._is_stage(project):
                parent, index = self._find_stage_parent(data, project)
                if parent is not None:
                    deleted_name = parent.stages[index].name
                    del parent.stages[index]
                    if not parent.stages:
                        parent.enable_stages = False
                    data['projects'][parent.name] = parent
                    en.save_data(data)
                    self.notifications.show_success(f'{deleted_name} удален.', position="bottom-left")
            elif project.name in data['projects']:
                del data['projects'][project.name]
                en.save_data(data)
                self.notifications.show_success(f'{project.name} удален.', position="bottom-left")

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)

    def on_archive_project_menu_triggered(self):
        """Обработчик меню 'Архивировать проект'"""
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Сначала выберите проект!")
            return
        if self._is_stage(project):
            self.notifications.show_warning("Этапы нельзя отправить в архив")
            return
        self.archive_project(project)

    def on_complete_project_menu_triggered(self):
        """Обработчик меню 'Завершить проект'"""
        project = self.get_current_project()
        if project is None:
            self.notifications.show_warning("Сначала выберите проект!")
            return

        # Дополнительная проверка: можно завершить только если цель достигнута
        if project.total_units < project.goal and project.goal != float('inf'):
            self.notifications.show_warning(
                "Нельзя завершить проект, пока не достигнута цель!"
            )
            return

        self.complete_project(project)

    def update_sync_status_label(self, project):
        """Обновляет текст метки с информацией о последней синхронизации."""
        if getattr(project, 'has_stages', lambda: False)():
            sync_dates = [stage.last_synch for stage in project.stages if stage.last_synch is not None]
            if sync_dates:
                dt_str = max(sync_dates).strftime('%d.%m.%Y %H:%M')
                self.synch_status.setText(f"Последняя синхр. этапов: {dt_str}")
            elif any(stage.synch is not None for stage in project.stages):
                self.synch_status.setText("Этапы подключены, еще не синхронизированы")
            else:
                self.synch_status.setText("Синхронизация этапов не настроена")
            return

        if project.last_synch:
            # Форматируем дату и время
            dt_str = project.last_synch.strftime('%d.%m.%Y %H:%M')
            self.synch_status.setText(f"Последняя синхр.: {dt_str}")
        else:
            self.synch_status.setText("Не синхронизирован")

    def background_synch(self, silent=False):
        data = en.load_data()
        projects = list(data['projects'].values())
        # Оставляем только проекты с настроенной синхронизацией
        projects_with_sync = []
        for project in projects:
            if getattr(project, 'has_stages', lambda: False)():
                projects_with_sync.extend(
                    stage for stage in project.stages
                    if stage.synch is not None and stage.status == 'активен'
                )
            elif project.synch is not None and project.status == 'активен':
                projects_with_sync.append(project)

        if not projects_with_sync:
            # Нет проектов для синхронизации — ничего не делаем
            return

        batch_id = object()
        self._background_sync_batches[batch_id] = {
            'queue': list(projects_with_sync),
            'completed': 0,
            'total': len(projects_with_sync),
            'silent': silent,
        }
        self._start_next_background_sync_item(batch_id)

    def written_today_in_all_projects(self):
        projects = en.load_data()['projects']
        total = 0
        for project in projects.values():
            project: en.Project = project
            added = en.unit_converter(project.unit, project.get_added_today_in_unit())
            total += added

        self.written_today_in_all_projects_label.setText(f'Написано сегодня {int(total)} сим.')


class ConfirmDialog(QDialog, confirm_dialog_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class CreateProject(QDialog, create_project_ui):
    def __init__(self, parent=None, existing_names=None, stage_mode=False, fixed_unit=None):
        super().__init__(parent)
        self.setupUi(self)
        self.existing_names = set(existing_names or [])
        self.stage_mode = stage_mode
        self.pending_stages = []

        # Словари для преобразования
        self.text_to_unit = {
            'Символы': 'symbols',
            'Листы А4': 'A4',
            'Авторские листы': 'author_list',
            'Страницы Фикбука': 'ficbook_pages'
        }
        self.unit_to_text = {v: k for k, v in self.text_to_unit.items()}

        # Текущая единица
        self.current_unit = fixed_unit or self.text_to_unit[self.cb_unit.currentText()]
        if fixed_unit:
            self.cb_unit.setCurrentText(self.unit_to_text[self.current_unit])

        # Скрываем предупреждения
        self.incorrect_data.setVisible(False)
        self.add_Stage.setVisible(False)
        if self.stage_mode:
            self.setWindowTitle("Создание этапа")
            self.enable_Stages.setVisible(False)
            self.add_Stage.setVisible(False)
            self.cb_unit.setVisible(False)
            self.label_7.setVisible(False)
        else:
            self.add_Stage.clicked.connect(self.add_stage)

        # Подключаем сигналы
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.de_deadline.dateChanged.connect(self.validate_all)
        self.de_deadline.dateChanged.connect(self.on_deadline_changed)
        self.le_name.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.on_deadline_changed)
        self.le_total_symbols.textChanged.connect(self.validate_all)
        self.le_total_symbols.textChanged.connect(self.on_total_symbols_changed)
        self.le_personal_goal_for_the_day.textChanged.connect(self.on_personal_goal_changed)
        if not self.stage_mode:
            self.cb_unit.currentTextChanged.connect(self.on_unit_changed)
        self.enable_Stages.toggled.connect(self.on_stages_toggled)

        # Флаг для предотвращения циклических обновлений
        self._updating = False

        # Устанавливаем минимальную дату - сегодня
        self.de_deadline.setMinimumDate(en.today_for_test())

        # Изначально кнопки должны быть активны, т.к. данные корректны
        self.buttons.setEnabled(True)

        # Вызываем обработчик чекбокса для начальной настройки
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # Вызываем валидацию для проверки всех полей
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.validate_all)

    def on_checkbox_toggled(self, checked):
        """Обработчик чекбокса 'Нет дедлайна'."""
        if checked:
            self.de_deadline.setDisabled(True)
            self.le_personal_goal_for_the_day.setDisabled(True)
            self.le_personal_goal_for_the_day.setText("0")
            self.incorrect_data.setVisible(False)
        else:
            self.de_deadline.setEnabled(True)
            self.de_deadline.setMinimumDate(en.today_for_test())
            self.le_personal_goal_for_the_day.setEnabled(True)
            self.on_deadline_changed()
        self.validate_all()

    def on_stages_toggled(self, checked):
        self.add_Stage.setVisible(checked and not self.stage_mode)
        self._update_add_stage_button_text()
        if checked:
            QMessageBox.information(
                self,
                "Этапы проекта",
                "Проект будет создан как проект с этапами. Текущие записи и прогресс будут помещены в первый этап, "
                "а общий прогресс проекта будет считаться по сумме целей и прогресса этапов."
            )
        else:
            QMessageBox.information(
                self,
                "Этапы проекта",
                "Если отключить этапы при редактировании, все записи этапов будут перенесены в проект "
                "в хронологическом порядке, а прогресс будет пересчитан как для одного проекта."
            )

    def _update_add_stage_button_text(self):
        if not hasattr(self, 'add_Stage'):
            return
        count = len(getattr(self, 'pending_stages', []))
        if count:
            self.add_Stage.setText(f"Добавить Этап ({count})")
        else:
            self.add_Stage.setText("Добавить Этап")

    def add_stage(self):
        stage_names = [stage.name for stage in self.pending_stages]
        dialog = CreateProject(
            parent=self,
            existing_names=stage_names,
            stage_mode=True,
            fixed_unit=self.current_unit,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        goal = dialog.get_goal()
        total = dialog.get_total()
        if self.current_unit != 'author_list':
            goal = math.ceil(goal)
            total = math.ceil(total)

        stage = en.Stage(
            name=dialog.get_name(),
            goal=goal,
            deadline=dialog.get_deadline(),
            total_symbols=total,
            unit=self.current_unit,
            personal_goal_for_the_day=dialog.get_personal_goal_for_the_day(),
        )
        stage.get_today_goal_value()
        self.pending_stages.append(stage)
        self._update_add_stage_button_text()

    def on_unit_changed(self, new_unit_text):
        """Конвертирует значения полей при смене единицы."""
        new_unit = self.text_to_unit[new_unit_text]

        # Если поля пустые - просто обновляем текущую единицу
        if not self.le_goal.text() or not self.le_total_symbols.text():
            self.current_unit = new_unit
            self.validate_all()
            return

        try:
            goal_val = float(self.le_goal.text())
            total_val = float(self.le_total_symbols.text())
        except ValueError:
            self.current_unit = new_unit
            self.validate_all()
            return

        # Конвертируем значения
        new_goal = en.unit_converter(self.current_unit, goal_val, new_unit)
        new_total = en.unit_converter(self.current_unit, total_val, new_unit)

        # Округляем до 2 знаков для отображения
        self.le_goal.setText(
            f"{new_goal:.2f}".rstrip('0').rstrip('.') if '.' in f"{new_goal:.2f}" else f"{new_goal:.0f}")
        self.le_total_symbols.setText(
            f"{new_total:.2f}".rstrip('0').rstrip('.') if '.' in f"{new_total:.2f}" else f"{new_total:.0f}")

        old_unit = self.current_unit
        self.current_unit = new_unit
        self._convert_pending_stages_unit(old_unit, new_unit)
        self.on_deadline_changed()
        self.validate_all()

    def _convert_pending_stages_unit(self, old_unit, new_unit):
        if old_unit == new_unit:
            return
        for stage in self.pending_stages:
            stage.goal = en.unit_converter(old_unit, stage.goal, new_unit)
            stage.total_units = en.unit_converter(old_unit, stage.total_units, new_unit)
            stage.unit = new_unit

    def on_total_symbols_changed(self):
        """При изменении текущего кол-ва: если дневная цель задана — пересчитывает дедлайн,
        иначе — пересчитывает дневную цель из дедлайна."""
        try:
            personal_goal = float(self.le_personal_goal_for_the_day.text())
        except (ValueError, AttributeError):
            personal_goal = 0
        if personal_goal > 0:
            self.on_personal_goal_changed()
        else:
            self.on_deadline_changed()

    def on_deadline_changed(self):
        """При изменении дедлайна пересчитывает дневную цель."""
        if self._updating or self.checkBox.isChecked():
            return
        try:
            goal = float(self.le_goal.text())
            total = float(self.le_total_symbols.text())
        except (ValueError, AttributeError):
            return
        remaining = goal - total
        if remaining <= 0:
            self._updating = True
            try:
                self.le_personal_goal_for_the_day.setText("0")
            finally:
                self._updating = False
            return
        deadline = self.de_deadline.date().toPython()
        today = en.today_for_test()
        days = (deadline - today).days + 1
        if days <= 0:
            daily = math.ceil(remaining)
        else:
            daily = remaining / days
        self._updating = True
        try:
            if self.current_unit == 'author_list':
                self.le_personal_goal_for_the_day.setText(f"{daily:.1f}")
            else:
                self.le_personal_goal_for_the_day.setText(str(math.ceil(daily)))
        finally:
            self._updating = False

    def on_personal_goal_changed(self):
        """При изменении дневной цели обновляет дедлайн, если нужно."""
        if self._updating or self.checkBox.isChecked():
            return
        try:
            personal_goal = float(self.le_personal_goal_for_the_day.text())
            goal = float(self.le_goal.text())
            total = float(self.le_total_symbols.text())
        except (ValueError, AttributeError):
            return
        if personal_goal <= 0 or goal <= total:
            return
        remaining = goal - total
        days_needed = math.ceil(remaining / personal_goal)
        today = en.today_for_test()
        computed_deadline = today + datetime.timedelta(days=days_needed - 1)
        self._updating = True
        try:
            qdate = QDate(computed_deadline.year, computed_deadline.month, computed_deadline.day)
            self.de_deadline.setDate(qdate)
        finally:
            self._updating = False

    def validate_all(self):
        """Валидация всех полей."""
        # Сбрасываем сообщения об ошибках (кроме имени, если оно есть)
        self.incorrect_data.setVisible(False)
        error_messages = []

        # Проверка имени
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)
        name_incorrect = current_name in self.existing_names and current_name != ""
        if name_incorrect:
            error_messages.append("Проект с таким именем уже существует")

        # Проверка дедлайна
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            selected_date = self.de_deadline.date().toPython()
            if selected_date < en.today_for_test():
                deadline_incorrect = True
                error_messages.append("Дедлайн не может быть в прошлом")

        # Проверка цели
        goal_text = self.le_goal.text().strip()
        goal_valid = False
        if goal_text:
            try:
                goal_val = float(goal_text)
                if goal_val > 0:
                    goal_valid = True
                else:
                    error_messages.append("Цель должна быть положительным числом")
            except ValueError:
                error_messages.append("Цель должна быть числом")
        else:
            error_messages.append("Введите цель")

        # Проверка текущего значения
        total_text = self.le_total_symbols.text().strip()
        total_valid = False
        if total_text:
            try:
                total_val = float(total_text)
                if total_val >= 0:
                    total_valid = True
                else:
                    error_messages.append("Текущее значение не может быть отрицательным")
            except ValueError:
                error_messages.append("Текущее значение должно быть числом")
        else:
            error_messages.append("Введите текущее значение")

        # Проверка что цель >= текущее значение (если оба валидны)
        goal_ge_total = True
        if goal_valid and total_valid:
            goal_val = float(goal_text)
            total_val = float(total_text)
            if goal_val < total_val:
                goal_ge_total = False
                error_messages.append("Цель должна быть больше или равна текущему значению")

        # Если есть ошибки, показываем первую в incorrect_data
        if error_messages:
            self.incorrect_data.setVisible(True)
            self.incorrect_data.setText("\n".join(error_messages[:1]))  # показываем первую ошибку
        else:
            self.incorrect_data.setVisible(False)

        # Финальное состояние кнопок
        buttons_enabled = (
                name_filled and not name_incorrect and
                not deadline_incorrect and
                goal_valid and total_valid and goal_ge_total
        )
        self.buttons.setEnabled(buttons_enabled)

    def get_goal(self):
        try:
            return float(self.le_goal.text())
        except:
            return 0

    def get_total(self):
        try:
            return float(self.le_total_symbols.text())
        except:
            return 0

    def get_unit(self):
        return self.current_unit

    def get_deadline(self):
        if self.checkBox.isChecked():
            return 'Нет'
        return self.de_deadline.date().toPython()

    def get_name(self):
        return self.le_name.text().strip()

    def get_personal_goal_for_the_day(self):
        if self.checkBox.isChecked():
            return 0
        try:
            val = float(self.le_personal_goal_for_the_day.text())
            return val
        except (ValueError, AttributeError):
            return 0

    def is_stages_enabled(self):
        return self.enable_Stages.isChecked()

    def get_pending_stages(self):
        return list(self.pending_stages)


class EditProject(QDialog, create_project_ui):
    def __init__(self, project, parent=None, existing_names=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Редактирование проекта')

        self.project = project
        self.original_name = project.name
        self.existing_names = set(existing_names or [])
        self.pending_stages = []

        # Словари для преобразования
        self.text_to_unit = {
            'Символы': 'symbols',
            'Листы А4': 'A4',
            'Авторские листы': 'author_list',
            'Страницы Фикбука': 'ficbook_pages'
        }
        self.unit_to_text = {v: k for k, v in self.text_to_unit.items()}

        # Текущая единица (из проекта)
        self.current_unit = project.unit
        self.cb_unit.setCurrentText(self.unit_to_text[self.current_unit])

        # Скрываем предупреждения
        self.incorrect_data.setVisible(False)

        # Заполняем поля данными из проекта
        self.le_name.setText(project.name)
        self.le_goal.setText(self._format_number(project.goal))
        self.le_total_symbols.setText(self._format_number(project.total_units))
        self.enable_Stages.setChecked(getattr(project, 'has_stages', lambda: False)())
        if isinstance(project, en.Stage):
            self.enable_Stages.setVisible(False)
            self.add_Stage.setVisible(False)
            self.cb_unit.setVisible(False)
            self.label_7.setVisible(False)
        else:
            self.add_Stage.setVisible(self.enable_Stages.isChecked())
            self.add_Stage.clicked.connect(self.add_stage)
            self._update_add_stage_button_text()

        if not isinstance(project, en.Stage) and project.has_stages():
            self.le_goal.setReadOnly(True)
            self.le_total_symbols.setReadOnly(True)
            self.le_goal.setToolTip("Цель родительского проекта складывается из целей этапов")
            self.le_total_symbols.setToolTip("Текущее количество родительского проекта складывается из этапов")
            self.le_goal.setStyleSheet("color: gray;")
            self.le_total_symbols.setStyleSheet("color: gray;")

        # Дедлайн
        if project.deadline != 'Нет':
            self.checkBox.setChecked(False)
            qdate = QDate(project.deadline.year, project.deadline.month, project.deadline.day)
            self.de_deadline.setDate(qdate)
            self.de_deadline.setEnabled(True)
        else:
            self.checkBox.setChecked(True)
            self.de_deadline.setDisabled(True)

        # Флаг для предотвращения циклических обновлений
        self._updating = False

        # Подключаем сигналы
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.de_deadline.dateChanged.connect(self.validate_all)
        self.de_deadline.dateChanged.connect(self.on_deadline_changed)
        self.le_name.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.on_deadline_changed)
        self.le_total_symbols.textChanged.connect(self.validate_all)
        self.le_total_symbols.textChanged.connect(self.on_total_symbols_changed)
        self.le_personal_goal_for_the_day.textChanged.connect(self.on_personal_goal_changed)
        self.cb_unit.currentTextChanged.connect(self.on_unit_changed)
        self.enable_Stages.toggled.connect(self.on_stages_toggled)

        # Устанавливаем минимальную дату - сегодня
        self.de_deadline.setMinimumDate(en.today_for_test())

        # Начальное состояние кнопок (после заполнения данных они должны быть активны)
        self.buttons.setEnabled(True)
        # on_checkbox_toggled выставит enabled/disabled и вызовет on_deadline_changed (автоматический расчёт)
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # Если у проекта сохранена своя дневная цель — восстанавливаем её поверх автоматической
        if project.deadline != 'Нет' and project.personal_goal_for_the_day and project.personal_goal_for_the_day > 0:
            self._updating = True
            try:
                self.le_personal_goal_for_the_day.setText(self._format_number(project.personal_goal_for_the_day))
            finally:
                self._updating = False

        QTimer.singleShot(0, self.validate_all)

    def _format_number(self, num):
        if isinstance(num, float) and num.is_integer():
            return str(int(num))
        return str(num)

    def on_checkbox_toggled(self, checked):
        if checked:
            self.de_deadline.setDisabled(True)
            self.le_personal_goal_for_the_day.setDisabled(True)
            self.le_personal_goal_for_the_day.setText("0")
            self.incorrect_data.setVisible(False)
        else:
            self.de_deadline.setEnabled(True)
            self.de_deadline.setMinimumDate(en.today_for_test())
            self.le_personal_goal_for_the_day.setEnabled(True)
            self.on_deadline_changed()
        self.validate_all()

    def on_stages_toggled(self, checked):
        self.add_Stage.setVisible(checked and not isinstance(self.project, en.Stage))
        self._update_add_stage_button_text()
        if checked:
            QMessageBox.information(
                self,
                "Этапы проекта",
                "Проект будет преобразован в проект с этапами. Все текущие записи автоматически перейдут "
                "в первый этап."
            )
        else:
            QMessageBox.information(
                self,
                "Этапы проекта",
                "Все записи этапов будут перенесены в проект в хронологическом порядке. Цели и прогресс этапов "
                "сложатся и будут пересчитаны как записи одного проекта."
            )

    def _update_add_stage_button_text(self):
        count = len(getattr(self, 'pending_stages', []))
        if count:
            self.add_Stage.setText(f"Добавить Этап ({count})")
        else:
            self.add_Stage.setText("Добавить Этап")

    def add_stage(self):
        existing_stage_names = [stage.name for stage in getattr(self.project, 'stages', [])]
        existing_stage_names.extend(stage.name for stage in self.pending_stages)
        dialog = CreateProject(
            parent=self,
            existing_names=existing_stage_names,
            stage_mode=True,
            fixed_unit=self.current_unit,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        goal = dialog.get_goal()
        total = dialog.get_total()
        if self.current_unit != 'author_list':
            goal = math.ceil(goal)
            total = math.ceil(total)

        stage = en.Stage(
            name=dialog.get_name(),
            goal=goal,
            deadline=dialog.get_deadline(),
            total_symbols=total,
            unit=self.current_unit,
            personal_goal_for_the_day=dialog.get_personal_goal_for_the_day(),
            parent_project_name=self.project.name,
        )
        stage.get_today_goal_value()
        self.pending_stages.append(stage)
        self._update_add_stage_button_text()

    def on_unit_changed(self, new_unit_text):
        new_unit = self.text_to_unit[new_unit_text]

        if not self.le_goal.text() or not self.le_total_symbols.text():
            self.current_unit = new_unit
            self.validate_all()
            return

        try:
            goal_val = float(self.le_goal.text())
            total_val = float(self.le_total_symbols.text())
        except ValueError:
            self.current_unit = new_unit
            self.validate_all()
            return

        new_goal = en.unit_converter(self.current_unit, goal_val, new_unit)
        new_total = en.unit_converter(self.current_unit, total_val, new_unit)

        self.le_goal.setText(self._format_number(new_goal))
        self.le_total_symbols.setText(self._format_number(new_total))

        old_unit = self.current_unit
        self.current_unit = new_unit
        self._convert_pending_stages_unit(old_unit, new_unit)
        self.on_deadline_changed()
        self.validate_all()

    def _convert_pending_stages_unit(self, old_unit, new_unit):
        if old_unit == new_unit:
            return
        for stage in self.pending_stages:
            stage.goal = en.unit_converter(old_unit, stage.goal, new_unit)
            stage.total_units = en.unit_converter(old_unit, stage.total_units, new_unit)
            stage.unit = new_unit

    def on_total_symbols_changed(self):
        """При изменении текущего кол-ва: если дневная цель задана — пересчитывает дедлайн,
        иначе — пересчитывает дневную цель из дедлайна."""
        try:
            personal_goal = float(self.le_personal_goal_for_the_day.text())
        except (ValueError, AttributeError):
            personal_goal = 0
        if personal_goal > 0:
            self.on_personal_goal_changed()
        else:
            self.on_deadline_changed()

    def on_deadline_changed(self):
        """При изменении дедлайна пересчитывает дневную цель."""
        if self._updating or self.checkBox.isChecked():
            return
        try:
            goal = float(self.le_goal.text())
            total = float(self.le_total_symbols.text())
        except (ValueError, AttributeError):
            return
        remaining = goal - total
        if remaining <= 0:
            self._updating = True
            try:
                self.le_personal_goal_for_the_day.setText("0")
            finally:
                self._updating = False
            return
        deadline = self.de_deadline.date().toPython()
        today = en.today_for_test()
        days = (deadline - today).days + 1
        if days <= 0:
            daily = math.ceil(remaining)
        else:
            daily = remaining / days
        self._updating = True
        try:
            if self.current_unit == 'author_list':
                self.le_personal_goal_for_the_day.setText(f"{daily:.1f}")
            else:
                self.le_personal_goal_for_the_day.setText(str(math.ceil(daily)))
        finally:
            self._updating = False

    def on_personal_goal_changed(self):
        """При изменении дневной цели обновляет дедлайн, если нужно."""
        if self._updating or self.checkBox.isChecked():
            return
        try:
            personal_goal = float(self.le_personal_goal_for_the_day.text())
            goal = float(self.le_goal.text())
            total = float(self.le_total_symbols.text())
        except (ValueError, AttributeError):
            return
        if personal_goal <= 0 or goal <= total:
            return
        remaining = goal - total
        days_needed = math.ceil(remaining / personal_goal)
        today = en.today_for_test()
        computed_deadline = today + datetime.timedelta(days=days_needed - 1)
        self._updating = True
        try:
            qdate = QDate(computed_deadline.year, computed_deadline.month, computed_deadline.day)
            self.de_deadline.setDate(qdate)
        finally:
            self._updating = False

    def validate_all(self):
        self.incorrect_data.setVisible(False)
        error_messages = []

        # Имя
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)
        name_incorrect = False
        if name_filled and current_name != self.original_name:
            name_incorrect = current_name in self.existing_names
        if name_incorrect:
            error_messages.append("Проект с таким именем уже существует")

        # Дедлайн
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            selected_date = self.de_deadline.date().toPython()
            if selected_date < en.today_for_test():
                deadline_incorrect = True
                error_messages.append("Дедлайн не может быть в прошлом")

        # Цель
        goal_text = self.le_goal.text().strip()
        goal_valid = False
        if goal_text:
            try:
                goal_val = float(goal_text)
                if goal_val > 0:
                    goal_valid = True
                else:
                    error_messages.append("Цель должна быть положительным числом")
            except ValueError:
                error_messages.append("Цель должна быть числом")
        else:
            error_messages.append("Введите цель")

        # Текущее значение
        total_text = self.le_total_symbols.text().strip()
        total_valid = False
        if total_text:
            try:
                total_val = float(total_text)
                if total_val >= 0:
                    total_valid = True
                else:
                    error_messages.append("Текущее значение не может быть отрицательным")
            except ValueError:
                error_messages.append("Текущее значение должно быть числом")
        else:
            error_messages.append("Введите текущее значение")

        # Цель >= текущее
        goal_ge_total = True
        if goal_valid and total_valid:
            goal_val = float(goal_text)
            total_val = float(total_text)
            if goal_val < total_val:
                goal_ge_total = False
                error_messages.append("Цель должна быть больше или равна текущему значению")

        if error_messages:
            self.incorrect_data.setVisible(True)
            self.incorrect_data.setText("\n".join(error_messages[:1]))
        else:
            self.incorrect_data.setVisible(False)

        buttons_enabled = (
                name_filled and not name_incorrect and
                not deadline_incorrect and
                goal_valid and total_valid and goal_ge_total
        )
        self.buttons.setEnabled(buttons_enabled)

    def get_goal(self):
        try:
            return float(self.le_goal.text())
        except:
            return self.project.goal

    def get_total(self):
        try:
            return float(self.le_total_symbols.text())
        except:
            return self.project.total_units

    def get_unit(self):
        return self.current_unit

    def get_deadline(self):
        if self.checkBox.isChecked():
            return 'Нет'
        return self.de_deadline.date().toPython()

    def get_name(self):
        return self.le_name.text().strip()

    def get_personal_goal_for_the_day(self):
        if self.checkBox.isChecked():
            return 0
        try:
            val = float(self.le_personal_goal_for_the_day.text())
            return val
        except (ValueError, AttributeError):
            return 0

    def is_stages_enabled(self):
        return self.enable_Stages.isChecked()

    def get_pending_stages(self):
        return list(self.pending_stages)


class NotificationManager:
    """Менеджер для показа уведомлений с поддержкой очереди и накопления."""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.toasts = []  # все активные уведомления в порядке добавления
        self.spacing = 10  # отступ между уведомлениями
        self.max_toasts = 5  # максимальное количество одновременно видимых
        self.margin = 5  # отступ от края окна

    def _compute_x(self, toast, position):
        """Вычисляет x-координату для уведомления в зависимости от его позиции и ширины."""
        parent_rect = self.parent.rect()
        width = toast.width()
        if position in ("top-right", "bottom-right"):
            return parent_rect.width() - width - self.margin
        elif position in ("top-left", "bottom-left"):
            return self.margin
        elif position in ("top-center", "bottom-center"):
            return (parent_rect.width() - width) // 2
        else:  # по умолчанию правый нижний
            return parent_rect.width() - width - self.margin

    def _rearrange_toasts(self):
        """Пересчитывает позиции всех уведомлений в зависимости от их положения."""
        # Группируем по позиции
        groups = {}
        for toast in self.toasts:
            pos = toast.position
            groups.setdefault(pos, []).append(toast)

        parent_rect = self.parent.rect()

        for position, toasts in groups.items():
            if position.startswith("top"):  # верхние позиции – новые сверху
                current_y = self.margin
                for toast in reversed(toasts):  # от новых к старым
                    x = self._compute_x(toast, position)
                    toast.set_global_position(x, current_y)
                    current_y += toast.height() + self.spacing

            elif position.startswith("bottom"):  # нижние позиции – новые снизу
                current_y = parent_rect.height() - self.margin
                for toast in reversed(toasts):  # от новых к старым
                    x = self._compute_x(toast, position)
                    current_y -= toast.height()
                    toast.set_global_position(x, current_y)
                    current_y -= self.spacing

            else:  # на случай других значений – просто по порядку сверху
                current_y = self.margin
                for toast in toasts:
                    x = self._compute_x(toast, position)
                    toast.set_global_position(x, current_y)
                    current_y += toast.height() + self.spacing

    def remove_toast_before_fade(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._rearrange_toasts()

    def _add_toast(self, toast):
        self.toasts.append(toast)
        # Убираем подключение к destroyed, теперь удаление происходит в remove_toast_before_fade
        if len(self.toasts) > self.max_toasts:
            oldest = self.toasts[0]
            oldest.start_fade_out()

        self._rearrange_toasts()
        toast.show()
        toast.fade_in_anim.start()

    def _duration_from_settings(self):
        duration_seconds = en.load_settings().get('notification_display_time', 10)
        try:
            duration_seconds = int(duration_seconds)
        except (TypeError, ValueError):
            duration_seconds = 10
        return max(1, duration_seconds) * 1000

    def _resolve_duration(self, duration):
        if duration is None:
            return self._duration_from_settings()
        return duration

    # В каждом методе показа передаём manager=self
    def show_success(self, message, duration=None, position="bottom-right"):
        duration = self._resolve_duration(duration)
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(76, 175, 80, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_error(self, message, duration=None, position="bottom-right"):
        duration = self._resolve_duration(duration)
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(244, 67, 54, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_warning(self, message, duration=None, position="bottom-right"):
        duration = self._resolve_duration(duration)
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 152, 0, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_info(self, message, duration=None, position="bottom-right"):
        duration = self._resolve_duration(duration)
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        self._add_toast(toast)


class Settings(QDialog, settings_ui):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Обрабатываем настройки
        settings = en.load_settings()
        if settings['inf_project'] is False:
            self.enable_inf_projects_checkBox.setChecked(False)
        else:
            self.enable_inf_projects_checkBox.setChecked(True)
        if settings['game_mode'] is False:
            self.enable_game_mode_checkBox.setChecked(False)
        else:
            self.enable_game_mode_checkBox.setChecked(True)
        if settings['global_streak'] is False:
            self.enable_global_streak_checkBox.setChecked(False)
        else:
            self.enable_global_streak_checkBox.setChecked(True)
        if not settings.get('show_written_today_in_all_projects', False):
            self.written_today_in_all_projects_checkBox.setChecked(False)
        else:
            self.written_today_in_all_projects_checkBox.setChecked(True)
        notification_display_time = settings.get('notification_display_time', 10)
        try:
            notification_display_time = int(notification_display_time)
        except (TypeError, ValueError):
            notification_display_time = 10
        self.notification_display_time_spinBox.setRange(1, 3600)
        self.notification_display_time_spinBox.setSuffix(' сек.')
        self.notification_display_time_spinBox.setValue(max(1, notification_display_time))


class UserAgreement(QDialog, user_agreement_ui):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


class ScrivenerItemDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите элемент Scrivener")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)

        label = QLabel("Выберите документ для синхронизации:")
        layout.addWidget(label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.selected_item = None

        # Заполняем дерево
        self.populate_tree(items)
        self.tree.itemDoubleClicked.connect(self.accept)

    def populate_tree(self, items, parent=None):
        for item in items:
            tree_item = QTreeWidgetItem(parent if parent else self.tree)
            tree_item.setText(0, item['title'])
            tree_item.setData(0, Qt.UserRole, item['id'])
            if item['children']:
                self.populate_tree(item['children'], tree_item)

    def get_selected_item(self):
        item = self.tree.currentItem()
        if item:
            item_id = item.data(0, Qt.UserRole)
            title = item.text(0)
            return item_id, title
        return None, None


class SynchWindow(QDialog, Ui_sych_window):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.project = project

        # Если уже есть синхронизация, устанавливаем соответствующий тип в комбобокс
        if project.synch and isinstance(project.synch, dict):
            if project.synch.get('type') == 'word':
                self.type_of_sych_cb.setCurrentText('Word')
            elif project.synch.get('type') == 'scrivener':
                self.type_of_sych_cb.setCurrentText('Scrivener')

        # Подключаем кнопки
        self.buttonBox.accepted.connect(self.on_accept)

    def on_accept(self):
        synch_type = self.type_of_sych_cb.currentText()

        if synch_type == 'Word':
            success = self.setup_word_sync()
        elif synch_type == 'Scrivener':
            success = self.setup_scrivener_sync()
        else:
            success = False

        if not success:
            # Оставляем диалог открытым
            return
        self.accept()

    def setup_word_sync(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл Word",
            "",
            "Документы Word (*.docx *.doc);;Все файлы (*)"
        )
        if not file_path:
            return False

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ('.docx', '.doc'):
            self.parent().notifications.show_error("Поддерживаются только .docx и .doc")
            return False

        self.project.synch = {'type': 'word', 'path': file_path}
        return True

    def setup_scrivener_sync(self):
        # Используем getOpenFileName, чтобы пользователь мог выбрать .scriv как файл
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите проект Scrivener (пакет .scriv)",
            "",
            "Проекты Scrivener (*.scriv);;Все файлы (*)"
        )
        if not file_path:
            return False

        # Проверяем, что это директория (пакет)
        if not os.path.isdir(file_path):
            self.parent().notifications.show_error(
                "Выбранный путь не является папкой проекта Scrivener.\n"
                "Убедитесь, что вы выбираете именно пакет .scriv."
            )
            return False

        # Поиск XML внутри пакета
        xml_path = find_scrivener_xml(file_path)
        if not xml_path:
            self.parent().notifications.show_error(
                "Не удалось найти файл проекта Scrivener внутри пакета.\n"
                "Убедитесь, что это корректный проект Scrivener."
            )
            return False

        # Парсинг элементов
        items = parse_scrivener_items(xml_path)
        if not items:
            self.parent().notifications.show_error(
                "Не удалось загрузить структуру проекта.\n"
                "Возможно, файл проекта повреждён."
            )
            return False

        # Диалог выбора элемента
        dialog = ScrivenerItemDialog(items, self)
        if dialog.exec() != QDialog.Accepted:
            return False

        item_id, item_title = dialog.get_selected_item()
        if not item_id:
            return False

        self.project.synch = {
            'type': 'scrivener',
            'path': file_path,  # сохраняем путь к пакету
            'item_id': item_id,
            'item_title': item_title
        }
        return True

class DeveloperMode(QDialog, Ui_developer_node):
    def __init__(self):
        super().__init__()
        gamer = game.load_game()
        settings = en.load_settings()
        self.setupUi(self)
        saved_test_datetime = settings.get('today_for_test_datetime')
        if settings.get('today_for_test_mode', False) and isinstance(saved_test_datetime, datetime.datetime):
            self.test_date_cb.setChecked(True)
            self.test_date.setEnabled(True)
            self.test_date.setDateTime(saved_test_datetime)
        else:
            self.test_date_cb.setChecked(False)
            self.test_date.setEnabled(False)
            self.test_date.setDateTime(datetime.datetime.now())

        self.level.setText(f'{gamer.level}')
        self.health.setText(f'{gamer.health}')
        self.coins.setText(f'{gamer.get_coins()}')
        self.exp.setText(f'{gamer.exp}')

        # Вызываем обработчик чекбокса для начальной настройки
        self.on_checkbox_toggled(self.test_date_cb.isChecked())
        # Подключаем сигнал чекбокса к обработчику
        self.test_date_cb.toggled.connect(self.on_checkbox_toggled)

    def get_today_for_test(self):
        if self.test_date_cb.isChecked():
            return self.test_date.dateTime().toPython()
        return None

    def on_checkbox_toggled(self, checked):
        """Обработчик чекбокса 'Нет дедлайна'."""
        if checked:
            self.test_date.setEnabled(True)
        else:
            self.test_date.setDisabled(True)


class ProjectStatsDialog(QDialog, project_stats_ui):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(f"Статистика — {project.name}")

        self.project = project
        self.fill_statistics()

    def fill_statistics(self):
        """Заполняет все лейблы статистики данными из проекта"""
        stats = self.project.get_statistic()

        # === Основные соответствия лейблов ===
        self.stat_notes_count.setText(str(stats['Кол-во записей']))

        self.stat_total_in_unit.setText(
            f"{self._format_number(stats['Всего написано в единице проекта'])} {self._get_unit_name()}"
        )

        self.stat_avg_symbols_per_active_day.setText(
            f"{stats['Среднее символов в день']} символов"
        )

        self.stat_avg_symbols_per_note.setText(
            f"{stats['Среднее кол-во символов в записи']} символов"
        )

        self.stat_avg_notes_per_day.setText(
            str(stats['Среднее кол-во записей в день'])
        )

        self.stat_freezes_used.setText(str(stats['Использовано заморозок']))

        self.stat_best_day.setText(stats['Лучший день'])

        self.stat_best_weekday.setText(stats['Самый продуктивный день недели'])

        self.stat_current_streak.setText(str(stats['Текущий стрик (дней)']))

        self.stat_max_streak.setText(str(stats['Максимальный стрик']))

        self.stat_days_since_start.setText(str(stats['Дней с начала проекта']))

        self.stat_active_days_count.setText(str(stats['Активных дней']))

        self.stat_active_days_percent.setText(stats['Процент активных дней'])

    def _format_number(self, num):
        """Форматирует числа для красивого отображения"""
        if isinstance(num, float):
            if num.is_integer():
                return str(int(num))
            return f"{num:.1f}".rstrip('0').rstrip('.')
        return str(num)

    def _get_unit_name(self):
        """Возвращает название единицы измерения проекта"""
        unit_map = {
            'symbols': 'символов',
            'A4': 'листов А4',
            'author_list': 'авторских листов',
            'ficbook_pages': 'страниц Ficbook'
        }
        return unit_map.get(self.project.unit, self.project.unit)


def _suppress_invalid_object_stderr_spam():
    """Глушит безобидную диагностику shiboken/Qt "Called attribute on
    invalid object", которая печатается при закрытии окна после выбора
    элемента списка с кастомным виджетом (setItemWidget + setCurrentItem).
    Сообщение пишется в файловый дескриптор stderr напрямую из C++,
    минуя sys.stderr, поэтому фильтруется на уровне ОС через pipe.
    Не влияет на работу приложения и не появляется в собранной сборке,
    но засоряет консоль при разработке.
    """
    if "__compiled__" in globals():
        return
    real_stderr_fd = os.dup(sys.stderr.fileno())
    read_fd, write_fd = os.pipe()
    os.dup2(write_fd, sys.stderr.fileno())
    os.close(write_fd)

    def _pump():
        real_stderr = os.fdopen(real_stderr_fd, "w")
        with os.fdopen(read_fd, "r", buffering=1) as pipe_reader:
            for line in pipe_reader:
                if "Called attribute on invalid object" not in line:
                    real_stderr.write(line)
                    real_stderr.flush()

    threading.Thread(target=_pump, daemon=True).start()


if __name__ == "__main__":
    updater_exit_code = run_windows_updater_from_argv()
    if updater_exit_code is not None:
        sys.exit(updater_exit_code)

    _suppress_invalid_object_stderr_spam()
    app = QApplication(sys.argv)

    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qt_ru", translations_path):
        app.installTranslator(translator)

    window = MainWindow()
    window.show()
    window.update_checker = UpdateChecker(window)
    QTimer.singleShot(1500, lambda: window.update_checker.check_for_updates(window))
    update_timer = QTimer(window)
    update_timer.setInterval(60 * 60 * 1000)
    update_timer.timeout.connect(lambda: window.update_checker.check_for_updates(window))
    update_timer.start()
    sys.exit(app.exec())
