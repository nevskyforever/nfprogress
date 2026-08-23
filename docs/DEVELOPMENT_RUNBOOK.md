# Запуск и сборка nfprogress

Этот документ описывает поддерживаемые варианты запуска из PyCharm и сборки
актуального Vue/Ionic-приложения поверх FastAPI. PySide6 больше не входит в
release-сборки и не поддерживается как пользовательская версия.

## Откуда запускать команды

Все команды ниже предполагают, что текущая папка терминала — **корень
репозитория**, то есть папка, где одновременно находятся `frontend/`,
`backend/` и `scripts/`. Если терминал открыт, например, в `docs/`, сначала
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
Vue/Ionic → FastAPI → services → Python Core → существующие .pkl-данные
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
2. Создайте interpreter на Python 3.13 в `.venv`.
3. Установите Python-зависимости:

   ```bash
   python3 -m pip install -r requirements-backend.txt
   ```

4. Для Vue/Ionic установите Node.js 20.19 или новее, затем один раз выполните:

   ```bash
   cd frontend
   npm ci
   ```

## Исторический PySide6-код

`main_UI.py` сохранён только как источник для регрессионного сравнения и
совместимости старых `.pkl`. Он не собирается в Actions, не публикуется и не
считается поддерживаемым способом запуска. Для desktop-разработки используйте
Tauri ниже.

## Новый Web-интерфейс

Для Web нужны два одновременно работающих процесса: FastAPI и Vite. В
обычном режиме разработки используйте тот же набор данных, что и
исторический Python UI: backend перед стартом обновляет `nfprogress/test_data` из более
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

Vite автоматически подхватывает изменения Vue и TypeScript, но запущенный
Python backend сам не перезапускается. После изменений в `backend/`,
`nfprogress/` или `engine.py` полностью остановите `Run Web.sh` сочетанием
`Ctrl+C` и запустите его снова. Иначе браузер продолжит обращаться к старому
FastAPI-процессу, даже если новый интерфейс уже появился после hot reload.

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

Для browser-проверок установлен Playwright. Один раз на каждой машине загрузите
управляемый Chromium, затем запускайте будущие browser-сценарии из того же
каталога:

```bash
npx playwright install chromium
npx playwright test
```

`npm run test` проверяет Vue-компоненты, а Playwright предназначен для
сквозных сценариев в реальном Chromium. Перед такими сценариями должен быть
запущен FastAPI backend с изолированными developer-данными.

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

Для локальных macOS-архивов доступны ARM/Intel/All-скрипты:

```bash
bash "Build Tauri ARM.sh"
bash "Build Tauri Intel.sh"
bash "Build Tauri All.sh"
```

Перед сборкой эти команды автоматически синхронизируют нормализованную версию
из `engine.py` с `tauri.conf.json`, `Cargo.toml` и `Cargo.lock`.

Они собирают подходящий Nuitka sidecar, Tauri `.app`, проверенный DMG и ZIP с
DMG, лицензией и сведениями об исходном коде. Результаты лежат в
`build-tauri-arm/` или `build-tauri-intel/`. На Apple Silicon Intel-сборка
требует x86_64 virtualenv с зависимостями backend; скрипт остановится с точной
командой, если вместо него выбран arm64 Python.

Скрипты `Release Tauri ARM.sh`, `Release Tauri Intel.sh` и
`Release Tauri All.sh` по умолчанию готовят только локальный архив. Подписанный
канал обновлений публикует защищённый CI workflow.

На macOS для обычного DMG без Finder/AppleScript-оформления используйте после
сборки соответствующего sidecar:

```bash
scripts/build-tauri-dmg.sh aarch64-apple-darwin
```

## Официальная Windows-сборка и обновления

`.github/workflows/build.yml` собирает только новую Tauri-версию на
Windows/MSVC. Он создаёт Nuitka sidecar и NSIS installer, проверяет запуск
sidecar, создаёт updater artifact с отдельной Tauri-подписью и публикует
`latest.json` в GitHub Releases. Windows-sidecar содержит иконку и версионные
метаданные и собирается без сжатия вложенного payload.

Перед первым запуском workflow настройте GitHub Actions:

- secrets `TAURI_SIGNING_PRIVATE_KEY` и, если задан,
  `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`;
- repository variable `TAURI_UPDATER_PUBLIC_KEY`.

Пара updater-ключей создаётся один раз командой из `frontend/`:

```powershell
npm run tauri signer generate -- -w "$env:USERPROFILE\.tauri\nfprogress-updater.key"
```

Это бесплатная пара ключей Tauri, а не сертификат Authenticode. Приватный ключ
нельзя коммитить или терять. Release-приложение проверяет
`latest.json` в GitHub Releases после запуска и раз в час; найденное обновление
устанавливается штатным Tauri updater только после проверки подписи. В
`tauri:dev` updater намеренно выключен.

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

- API documentation: `http://127.0.0.1:8000/docs`.
- Vue development server: `http://127.0.0.1:5173`.
- Архитектура: `docs/frontend-migration/ARCHITECTURE.md`.
- Текущий статус и platform-specific ограничения:
  `docs/frontend-migration/MIGRATION_STATUS.md`.
