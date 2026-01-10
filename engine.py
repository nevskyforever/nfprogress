import pickle
import game
from datetime import date, datetime, timedelta

def load_projects():
	try:
		with open('projects.pkl', 'rb') as f:
			projects = pickle.load(f)
			return projects
	except FileNotFoundError:
		return {'last': None}

def save_projects(projects):
	with open('projects.pkl', 'wb') as f:
		pickle.dump(projects, f)

def update_project():
	pass

def main_menu():
	print('nfprogress 0.10\n')
	print('Что вы хотите сделать?\n')
	print('1 - Новая запись')
	print('2 - Просмотр проектов')
	print('3 - Новый проект')
	print('4 - Изменить проект')
	print('5 - Игровой режим')
	last = load_projects()['last']
	if last is not None:
		print(f'Запись в последний проект ({last}) - Enter')
	do_list = {'1': new_note,
	'2': view_projects,
	'3': new_project,
	'4': change_project,
	'5': game.menu}
	update_project()
	do = input('\nВыберите пункт из меню: ')
	if do != '':
		try:
			do_list[do]()
		except KeyError:
			print('НЕПРАВИЛЬНЫЙ ВЫБОР')
			main_menu()
	else:
		new_note(last)

def new_project():
	projects = load_projects()
	print('\nСОЗДАНИЕ ПРОЕКТА\n')
	name = input('Введите имя проекта: ')
	try:
		goal = int(input('Введите цель по проекту в символах: '))
	except ValueError:
		print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
		goal = int(input('Введите цель по проекту в символах: '))
	projects[name] = {'goal': goal,
	'created': date.today(),
	'total symbols': 0,
	'progress': 0,
	'notes': {},
	'streaks': [],
	'deadline': {'date': 'Нет', 'days left': 0}}
	save_projects(projects)
	print(f'\nПроект {name} создан\n')
	main_menu()

def view_projects():
	projects = load_projects()
	if len(projects) == 1:
		print('\nПроектов пока нет.')
		do = input('\nДля выхода нажмите Enter.')
		if do == '':
			main_menu()
	else:
		for name in projects.keys():
			if name != 'last':
				goal = projects[name]['goal']
				progress = projects[name]['progress']
				symbols = projects[name]['total symbols']
				deadline = projects[name]['deadline']['date']
				if deadline == 'Нет':
					print(f'Название: {name}, '
					f'прогресс: {progress}%, '
					f'написано/цель: {symbols}/{goal} символов')
				else:
					deadline = datetime.strftime(deadline, '%d.%m.%y')
					days_left = projects[name]['deadline']['days left']
					streaks = len(projects[name]['streaks'])
					print(f'Название: {name}, '
					f'прогресс: {progress}%, '
					f'написано/цель: {symbols}/{goal} символов, '
					f'дедлайн: {deadline}, осталось дней: {days_left} '
					f'стрик: {streaks}')
		do = input('\nДля выхода нажмите Enter.')
		if do == '':
			main_menu()

def choice_project():
	projects = load_projects()
	if len(projects) == 1:
		print('\nПроектов пока нет.')
		do = input('\nДля выхода нажмите Enter.')
		if do == '':
			main_menu()
	else:
		projects_names = list(projects.keys())
		l = projects_names.index('last')
		del projects_names[l]
		print('ВЫБЕРИТЕ ПРОЕКТ:\n')
		for i in range(len(projects_names)):
			print(f'{i + 1} - {projects_names[i]}')
		try:
			choice = int(input('\nВведите номер выбранного проекта '
			'\nили введите Enter для выхода в главное меню: '))
			choice = projects_names[choice - 1]
			print(f'\nВыбран проект: {choice}\n')
			return choice
		except (ValueError, IndexError):
			print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
			main_menu()

def chek_streak(project):
	projects = load_projects()
	streaks = projects[project]['streaks']
	today = date.today()
	streak_status = None
	if len(streaks) == 0:
		streaks.append(today)
		streak_status = 'Start'
	else:
		yesterday = today - timedelta(days=1)
		if streaks[-1] == yesterday:
			streaks.append(today)
			streak_status = 'Go'
		else:
			streak_status = f'Lose {len(streaks)}'
			streaks = [today]
	projects[project]['streaks'] = streaks
	save_projects(projects)
	return streak_status

def new_note(choice=None):
	print('\nСОЗДАНИЕ ЗАПИСИ\n')
	projects = load_projects()
	game_status = game.load_game()
	if choice is None:
		choice = choice_project()
		if choice is None:
			return
	projects['last'] = choice
	deadline = projects[choice]['deadline']['date']
	goal = projects[choice]['goal']
	today = date.today()
	today_goal = 0
	last_total = projects[choice]['total symbols']
	if deadline != 'Нет':
		days_left = (deadline - today).days
		if days_left > 0:
			today_goal = round((goal - last_total) / days_left)
	print(f'\n Цель на сегодня: {today_goal} сим. \n')
	try:
		new_symbols = int(input(f'Введите текущее кол-во символов в {choice}: '))
	except ValueError:
		print('НЕКОРРЕКТНОЕ ЗНАЧЕНИЕ.\n Введите число.')
		new_symbols = int(input('Введите текущее кол-во символов: '))
	projects[choice]['total symbols'] = new_symbols
	symbol_progress = new_symbols - last_total
	progress = new_symbols // goal * 100 if goal > 0 else 0
	projects[choice]['progress'] = progress
	if deadline != 'Нет' and today_goal <= symbol_progress:
		streak_status = chek_streak(choice)
		if streak_status == 'Go':
			print('Стрик продолжен! Так держать!')
		elif streak_status == 'Start':
			print('Ты начал путь к цели!')
		elif streak_status.startswith('Lose'):
			lose = int(streak_status.split()[-1])
			print(f'Стрик прерван! Потеряно {lose} дн. Ты начал его сначала, не сдавайся!')
		if game_status is not None:
            if streak_status == 'Start':
			    print(game.give_streak_bonus(streak_status))
	else:
		if game_status is not None and symbol_progress > 0:
			exp_earned = game.give_exps(symbol_progress)
			coins_earned = game.give_coins(symbol_progress)
			print(f'Заработано: {coins_earned} монет, {exp_earned} опыта')
	save_projects(projects)
	do = input(f'\nЗапись добавлена в {choice}, прогресс: {progress}% и {symbol_progress} символов\n'
	f'\nВыйти в главное меню - Enter.')
	if do == '':
		main_menu()

def change_project():
	print('\nИЗМЕНЕНИЕ ПРОЕКТА\n')
	projects = load_projects()
	choice = choice_project()
	if choice is None:
		return

	def change_name():
		new_name = input(f'Введите новое имя проекта {choice} или Enter для выхода: ')
		if new_name != '':
			projects[new_name] = projects[choice]
			del projects[choice]
			save_projects(projects)
			print(f'\nИмя изменено на {new_name}.\n')
			main_menu()
		else:
			main_menu()

	def change_goal():
		try:
			new_goal = int(input(f'Введите новую цель для {choice} или Enter для выхода: '))
			if new_goal > 0:
				projects[choice]['goal'] = new_goal
				save_projects(projects)
				print(f'Цель {choice} изменена на {new_goal}')
				main_menu()
			else:
				print('Цель должна быть больше 0')
				change_goal()
		except ValueError:
			print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
			change_goal()

	def change_deadline():
		deadline_str = input('Введите дату дедлайна в формате "дд.мм.гг" или Enter: ')
		if deadline_str == '':
			main_menu()
			return
		try:
			new_deadline = datetime.strptime(deadline_str, '%d.%m.%y')
			projects[choice]['deadline'] = {
			'date': new_deadline.date(),
			'days left': (new_deadline.date() - date.today()).days
			}
			save_projects(projects)
			print(f'\nДедлайн {choice} изменён на {deadline_str}.')
			main_menu()
		except ValueError:
			print('Формат: дд.мм.гг')
			change_deadline()

	def delete_project():
		from random import randint
		key = randint(1000, 9999)
		print(f'Если вы удалите {choice}, все его данные будут стерты без возможности восстановления \n')
		try:
			approve = int(input(f'Подтвердите удаление введя {key}: '))
			if approve == key:
				print(f'\n {choice} удален. \n')
				del projects[choice]
				save_projects(projects)
				main_menu()
			else:
				print('\n УДАЛЕНИЕ НЕ ПОДТВЕРЖДЕНО \n')
				main_menu()
		except ValueError:
			print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ')
			main_menu()

	def change_total_symbols():
		print('Это изменение меняет текущий прогресс напрямую.')
		try:
			new_symbols = int(input(f'Введите новое кол-во символов в {choice}: '))
			if new_symbols >= 0:
				projects[choice]['total symbols'] = new_symbols
				goal = projects[choice]['goal']
				progress = new_symbols // goal * 100 if goal > 0 else 0
				projects[choice]['progress'] = progress
				save_projects(projects)
				print('\n ИЗМЕНЕНИЯ ПРИМЕНЕНЫ \n')
				main_menu()
			else:
				print('Количество символов не может быть отрицательным')
				change_total_symbols()
		except ValueError:
			print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
			change_total_symbols()

	change_list = {'1': change_name,
	'2': change_goal,
	'3': change_deadline,
	'4': delete_project,
	'5': change_total_symbols}

	print(f'1 - изменить имя проекта {choice}')
	print(f'2 - изменить цель проекта {choice}')
	print(f'3 - изменить дедлайн проекта {choice}')
	print(f'4 - удалить проект {choice}')
	print(f'5 - Изменить общее кол-во символов в {choice}')
	print(f'\nВыйти в главное меню - Enter\n')
	do = input('Выберите пункт из меню: ')
	if do == '':
		main_menu()
	elif do in change_list:
		change_list[do]()
	else:
		print('НЕПРАВИЛЬНЫЙ ВЫБОР')
		main_menu()

main_menu()