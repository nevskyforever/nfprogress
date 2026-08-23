# Запуск и сборка nfprogress

Этот документ описывает варианты запуска из PyCharm и сборки на текущем
переходном этапе: legacy-интерфейс на PySide6 продолжает быть release-версией,
а новый интерфейс работает как Vue/Ionic-клиент поверх FastAPI.

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

Для Web нужны два одновременно работающих процесса: FastAPI и Vite.

### 1. FastAPI

В PyCharm создайте конфигурацию **Python** с запуском по имени модуля:

- **Module name:** `backend.app`
- **Parameters:**

  ```text
  --host 127.0.0.1 --port 8000 --platform web --data-dir /tmp/nfprogress-api-dev
  ```

- **Working directory:** `$PROJECT_DIR$`
- **Python interpreter:** `.venv`

`--data-dir` создаёт изолированное тестовое хранилище. Это безопаснее, чем
проверять новый API на реальных пользовательских данных. После запуска API
доступен по адресам:

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
python3 -m backend.app --host 127.0.0.1 --port 8000 --platform web --data-dir /tmp/nfprogress-api-dev
```

В PyCharm backend нужно запускать именно как модуль `backend.app`, а не как
файл `backend/app/main.py`: последний создаёт FastAPI-приложение, но сам
Uvicorn-сервер не запускает. В активированном виртуальном окружении допустима
команда `python`, но в текущей macOS-среде доступна команда `python3`.

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
python3 -m pip install nuitka
python3 scripts/build-backend-sidecar.py
cd frontend
npm ci
npm run tauri:dev
```

`tauri:dev` самостоятельно запускает Tauri-окно и локальный backend. Вручную
запускать FastAPI для него не нужно.

Production-сборка:

```bash
cd frontend
npm run tauri:build
```

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
