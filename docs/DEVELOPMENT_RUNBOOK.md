# Запуск и сборка nfprogress

Этот документ описывает варианты запуска из PyCharm и сборки на текущем
переходном этапе: legacy-интерфейс на PySide6 продолжает быть release-версией,
а новый интерфейс работает как Vue/Ionic-клиент поверх FastAPI.

## Откуда запускать команды

Все команды ниже предполагают, что текущая папка терминала — **корень
репозитория**, то есть папка, где одновременно находятся `main_UI.py`,
`frontend/` и `scripts/`. Если терминал открыт, например, в `docs/`, сначала
выполните:

```bash
cd "$(git rev-parse --show-toplevel)"
```

Проверка должна вывести путь, содержащий `frontend/package-lock.json` и
`scripts/build-backend-sidecar.py`:

```bash
pwd
```

## Как устроено приложение

```text
Legacy PySide6 UI ────────────────┐
                                  ├─ Python Core → существующие .pkl-данные
Vue/Ionic → FastAPI → services ──┘
     ├─ Web
     ├─ Tauri для desktop
     └─ Capacitor для iOS/Android
```

Расчёты прогресса, игры и сохранение данных остаются в Python. Новый frontend
не читает `.pkl` напрямую: он обращается к FastAPI. Tauri запускает FastAPI как
локальный упакованный Python sidecar, а Web и мобильные клиенты подключаются к
отдельно запущенному FastAPI по HTTP(S).

## Подготовка PyCharm

1. Откройте корень репозитория в PyCharm.
2. Создайте interpreter на Python 3.11 в `.venv`.
3. Установите Python-зависимости:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

4. Для Vue/Ionic установите Node.js 20.19 или новее, затем один раз выполните:

   ```bash
   cd frontend
   npm ci
   ```

## Legacy desktop (PySide6)

Это самый простой вариант запуска обычного desktop-приложения.

В **Run | Edit Configurations** создайте конфигурацию типа **Python**:

- **Script path:** `$PROJECT_DIR$/main_UI.py`
- **Working directory:** `$PROJECT_DIR$`
- **Python interpreter:** `.venv`

Запуск из исходников включает developer-режим. Его данные находятся в
`nfprogress/test_data`; перед первым запуском туда копируются более новые
основные `.pkl`-файлы. Не используйте его одновременно с новым backend по той
же папке данных.

## Новый Web-интерфейс

Для Web нужны два одновременно работающих процесса: FastAPI и Vite. В
обычном режиме разработки используйте тот же набор данных, что и
`main_UI.py`: backend перед стартом обновляет `nfprogress/test_data` из более
новых рабочих `.pkl`, а все записи нового интерфейса идут в эту тестовую
копию.

### 1. FastAPI

В PyCharm создайте конфигурацию **Python** с запуском по имени модуля:

- **Module name:** `backend.app`
- **Parameters:**

  ```text
  --host 127.0.0.1 --port 8000 --platform web --dev-data
  ```

- **Working directory:** `$PROJECT_DIR$`
- **Python interpreter:** `.venv`

`--dev-data` включает Python-совместимый режим: вызывается тот же
`engine.sync_test_data()`, что и при запуске `main_UI.py`, затем backend
работает с `~/Documents/nfprogress/test_data` (или платформенным каталогом
данных nfprogress). Исходные рабочие `.pkl` не перезаписываются. Для полностью
пустых изолированных тестов по-прежнему можно указать `--data-dir` вместо
`--dev-data`. После запуска API доступен по адресам:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 2. Vue/Ionic

Создайте конфигурацию типа **npm**:

- **package.json:** `$PROJECT_DIR$/frontend/package.json`
- **Script:** `dev`

Или выполните во встроенном терминале PyCharm:

```bash
cd frontend
npm run dev
```

Откройте `http://127.0.0.1:5173`. Vite перенаправляет `/api` и `/health` на
FastAPI по адресу `127.0.0.1:8000`.

Сначала запускайте FastAPI, затем Vite. Не запускайте одновременно
`main_UI.py` и backend, если оба используют одну и ту же папку данных.

### Ошибка «API вернул ошибку 502»

Она означает, что Vite работает, но не может достучаться до FastAPI на
`127.0.0.1:8000`. Проверьте API напрямую:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ содержит `"status":"ok"`. Если соединение отклонено,
запустите backend из корня репозитория:

```bash
python3 -m backend.app --host 127.0.0.1 --port 8000 --platform web --dev-data
```

В PyCharm backend нужно запускать именно как модуль `backend.app`, а не как
файл `backend/app/main.py`: последний создаёт FastAPI-приложение, но сам
Uvicorn-сервер не запускает. В активированном виртуальном окружении допустима
команда `python`, но в текущей macOS-среде доступна команда `python3`.

Для запуска Web без двух отдельных терминалов используйте из корня:

```bash
bash "Run Web.sh"
```

Скрипт запускает FastAPI с `--dev-data`, ждёт `/health`, затем запускает Vite.
При остановке Vite дочерний backend также завершается. Проверка зависимостей без
запуска выполняется командой `bash "Run Web.sh" --check`.

## Проверки и Web-сборка

Python-проверки из корня репозитория:

```bash
python3 -m pytest -q
```

Frontend-проверки и production-сборка из `frontend/`:

```bash
npm run typecheck
npm run lint
npm run test
npm run build
```

Готовый Web-frontend появится в `frontend/dist`. Для размещения в интернете
нужны отдельный FastAPI-сервер, HTTPS и настройка хоста, который отдаёт
`index.html` для маршрутов Vue Router.

## Новый desktop-вариант Tauri

Нужны Rust/Cargo, Node.js и Nuitka. Сначала соберите Python sidecar под текущую
платформу:

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m pip install nuitka
python3 scripts/build-backend-sidecar.py
cd frontend
npm ci
npm run tauri:dev
```

`tauri:dev` самостоятельно запускает Tauri-окно и локальный backend. Вручную
запускать FastAPI для него не нужно.

Для обычного локального запуска нового desktop-приложения без production-пакета
используйте из корня репозитория:

```bash
bash "Run Tauri.sh"
```

Скрипт выбирает Rust architecture текущего Mac, использует matching sidecar и
использует Python-совместимую папку `test_data` и синхронизирует её при старте.
Если sidecar отсутствует, не поддерживает dev-режим или старее Python-кода
backend, скрипт пересоберёт только этот локальный Python backend; production `.app`, DMG и ZIP
при этом не создаются.
Проверить prerequisites без открытия окна можно так:

```bash
bash "Run Tauri.sh" --check
```

Перед запуском остановите отдельный npm run dev, если он уже занимает порт
5173. Первый Tauri dev-start может скомпилировать debug Rust-код, но не создаёт
production .app, DMG или ZIP.

Если в терминале Tauri появляется Vite-сообщение
API вернул ошибку 502 или connect ECONNREFUSED 127.0.0.1:8000 **до** строки
Running target/debug/nfprogress-desktop, обычно его отправляет ранее открытая
браузерная вкладка с адресом 127.0.0.1:5173. Эта вкладка тестирует Web-режим и
ищет отдельный FastAPI на порту 8000. Закройте её или запускайте для неё
backend отдельно. Сам Tauri не использует порт 8000: он запускает свой sidecar
на случайном loopback-порту с session token. Проверяйте работу в открывшемся
desktop-окне nfprogress, а не в браузере.

Production-сборка:

```bash
cd frontend
npm run tauri:build
```

Для локальных macOS-архивов есть те же ARM/Intel/All-скрипты, что и для
legacy PySide6-версии:

```bash
bash "Build Tauri ARM.sh"
bash "Build Tauri Intel.sh"
bash "Build Tauri All.sh"
```

Они собирают подходящий Nuitka sidecar, Tauri `.app`, проверенный DMG и ZIP с
DMG, лицензией и сведениями об исходном коде. Результаты лежат в
`build-tauri-arm/` или `build-tauri-intel/`. На Apple Silicon Intel-сборка
требует x86_64 virtualenv с зависимостями backend; скрипт остановится с точной
командой, если вместо него выбран arm64 Python.

Скрипты `Release Tauri ARM.sh`, `Release Tauri Intel.sh` и
`Release Tauri All.sh` также существуют, но по умолчанию готовят только
локальный архив. Загрузка требует явного `NFPROGRESS_TAURI_RELEASE_UPLOAD=1`
и никогда не меняет legacy update manifest: подписанный Tauri release-канал
ещё не введён.

На macOS для обычного DMG без Finder/AppleScript-оформления используйте после
сборки соответствующего sidecar:

```bash
scripts/build-tauri-dmg.sh aarch64-apple-darwin
```

## Legacy macOS-сборка

Для текущего PySide6-приложения на Apple Silicon:

```bash
bash scripts/build-macos-local.sh arm
```

Intel-сборка требует совместимого Intel-окружения:

```bash
bash scripts/build-macos-local.sh intel
```

Официальная Windows-сборка рассчитана на Windows/MSVC CI. Не собирайте её
кросс-компиляцией с macOS.

## iOS и Android

Capacitor не запускает Python внутри приложения: ему нужен опубликованный
FastAPI по HTTPS. Сначала задайте URL backend и синхронизируйте Web-ресурсы:

```bash
cd frontend
VITE_API_BASE_URL=https://api.example.com npm run cap:sync
```

Затем открывайте `frontend/ios` в Xcode либо `frontend/android` в Android
Studio. Для нативной сборки нужны полный Xcode с iPhoneOS SDK либо поддерживаемые
JDK и Android SDK соответственно.

## Полезные адреса и документы

- Legacy entry point: `main_UI.py`.
- API documentation: `http://127.0.0.1:8000/docs`.
- Vue development server: `http://127.0.0.1:5173`.
- Архитектура: `docs/frontend-migration/ARCHITECTURE.md`.
- Текущий статус и platform-specific ограничения:
  `docs/frontend-migration/MIGRATION_STATUS.md`.
