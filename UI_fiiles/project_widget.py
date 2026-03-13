# =============================================================================
# Финальный класс виджета проекта (используется в main_UI.py)
# =============================================================================
class ProjectWidget(QWidget, Ui_Form):
    def __init__(self, project, global_streak_mode):
        super().__init__()
        self.setupUi(self)
        # Загружаем настройки
        self.global_streak_mode = global_streak_mode
        # 1. Сбрасываем фиксированный размер, установленный в .ui
        self.resize(0, 0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        # 2. Удаляем стандартный QProgressBar
        self.progressBar.deleteLater()

        # 3. Создаём круговой прогресс-бар
        self.circular_progress = CircularProgressBar(self.widget)
        self.circular_progress.setTextVisible(False)
        self.circular_progress.setRingWidth(12)

        # ВАЖНО: Устанавливаем фиксированный размер ДО добавления в сетку
        self.circular_progress.setFixedSize(90, 90)

        # Устанавливаем цвета градиента
        self.circular_progress.setStartColor("#FF0000")  # красный для 0%
        self.circular_progress.setEndColor("#4CAF50")  # зелёный для 100%
        self.circular_progress.setBackgroundColor("#E0E0E0")

        # Убираем Expanding политику, так как размер фиксированный
        self.circular_progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 4. Заменяем старый прогресс-бар в сетке
        self.gridLayout.addWidget(self.circular_progress, 1, 0, 1, 1)

        # 5. Центрируем в ячейке
        self.gridLayout.setAlignment(self.circular_progress, Qt.AlignCenter)

        # --- ИСПРАВЛЕНИЕ: настройка растяжения строк для равномерного распределения ---
        # Устанавливаем одинаковый коэффициент растяжения для всех строк
        for row in range(6):  # всего 6 строк (0-5)
            self.gridLayout.setRowStretch(row, 1)

        # Устанавливаем минимальную высоту для строк с текстом
        self.gridLayout.setRowMinimumHeight(0, 30)  # name
        self.gridLayout.setRowMinimumHeight(2, 30)  # symbols
        self.gridLayout.setRowMinimumHeight(3, 30)  # deadline
        self.gridLayout.setRowMinimumHeight(4, 30)  # streak
        self.gridLayout.setRowMinimumHeight(5, 30)  # streak_status

        # 6. Обеспечиваем, что внутренний виджет-контейнер расширяется
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- УЛУЧШЕНО: настройка текстовых меток ---
        for label in (self.name, self.symbols, self.deadline,
                      self.streak, self.streak_status):
            label.setWordWrap(True)  # разрешаем перенос строк
            label.setAlignment(Qt.AlignCenter)  # центрируем текст
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

            # Устанавливаем минимальную высоту для меток
            label.setMinimumHeight(30)

            # Настраиваем шрифт для лучшей читаемости
            font = label.font()
            font.setPointSize(10)  # фиксированный размер шрифта
            font.setBold(False)
            label.setFont(font)

        # Добавляем отступы в сетке
        self.gridLayout.setSpacing(5)  # расстояние между элементами
        self.gridLayout.setContentsMargins(10, 10, 10, 10)  # отступы от краёв

        self.project = project
        self.circular_progress.lower()
        self.update_display()

    def update_display(self):
        """Обновляет отображение виджета проекта."""
        self.name.setText(self.project.name)

        # Прогресс (всегда в процентах)
        self.circular_progress.setValue(int(self.project.progress), animated=True)

        # Значения уже в единице проекта
        total_str = self._format_number(self.project.total_symbols)
        goal_str = self._format_number(self.project.goal)
        self.symbols.setText(f'{total_str} / {goal_str}')

        # Сначала скрываем все элементы стриков
        self.streak.setVisible(False)
        self.streak_status.setVisible(False)

        # Дедлайн
        if self.project.deadline_str != 'Нет':
            self.deadline.setText(f'Дедлайн: {self.project.deadline_str}')
            self.deadline.setVisible(True)

            # Показываем стрики только если они включены в настройках
            if self.global_streak_mode:
                streak_status = self.project.get_streak_status()
                streak_length = len(self.project.streaks)
                self.streak.setText(f'Стрик: {streak_length} д.')
                self.streak.setVisible(True)

                status_msg = self.project.get_streak_status_msg('min')
                self.streak_status.setText(status_msg)
                self.streak_status.setVisible(True)
        else:
            self.deadline.setVisible(False)

        # Обновляем геометрию
        self.updateGeometry()
        self.widget.updateGeometry()

    def _format_number(self, num):
        """Форматирует число для отображения."""
        if isinstance(num, float):
            if num.is_integer() or abs(num - round(num)) < 0.0001:
                return str(int(round(num)))
            # Оставляем 1-2 знака после запятой, убираем лишние нули
            return f"{num:.2f}".rstrip('0').rstrip('.') if '.' in f"{num:.2f}" else str(int(num))
        return str(num)