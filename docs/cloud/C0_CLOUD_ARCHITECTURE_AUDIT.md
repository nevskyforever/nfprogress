# C0 — аудит архитектуры Web/cloud

Дата аудита: 2026-09-20.  Источник фактов — ветка `6.0`.

## 1. Текущее состояние архитектуры

Поддерживаемый интерфейс расположен в `frontend/`: Vue 3 + TypeScript +
Ionic. Один и тот же frontend запускается в трёх разных средах, но их пути
данных сейчас неравнозначны:

- **Desktop/Tauri** уже local-first: normal runtime не запускает Python или
  FastAPI. Vue вызывает typed Tauri commands; Rust открывает локальный
  `nfprogress.db` через `rusqlite`.
- **Web** — HTTP-клиент текущего FastAPI compatibility backend. Это не cloud
  backend: сервер использует Python domain services и файловый
  `PickleRepository` конкретного data directory.
- **iOS/Android/Capacitor** имеют оболочку и platform detection, но пока идут
  по тому же HTTP API, что и Web. Локального SQLite repository и Sync Engine
  в Capacitor нет.

```text
Desktop (сейчас и далее, local-first)
Vue / TypeScript → Tauri / Rust → local SQLite (+ user-owned files)
                                      ↕ future Sync Engine ↕ HTTPS → Cloud API

Android (будущий local-first путь)
Vue / Ionic / Capacitor → local SQLite
                               ↕ future Sync Engine ↕ HTTPS → Cloud API

Web (будущий cloud path)
Vue / Ionic → HTTPS → FastAPI → PostgreSQL

Cloud (будущий)
FastAPI → PostgreSQL
        → encrypted object/file storage (не PostgreSQL binary column)
```

Это подтверждает границу, которую нельзя нарушать: normal Desktop path —
`Vue → TS → Tauri/Rust → SQLite`; FastAPI/Python не возвращается в startup,
loopback sidecar или fallback desktop runtime. Web/cloud — отдельно
развёрнутый `Vue → HTTPS → FastAPI → PostgreSQL` путь.

## 2. Текущий Web request/data flow

`frontend/src/api/client.ts` берёт public build-time
`VITE_API_BASE_URL`, удаляет завершающий `/` и выполняет `fetch`; при пустом
значении используются относительные `/api/...` URL. Vite development proxy в
`frontend/vite.config.ts` направляет `/api` и `/health` на
`127.0.0.1:8000`. Клиент не добавляет token, cookies или auth state.

`Run Web.sh` запускает `python3 -m backend.app --platform web --dev-data` и
Vite. `--dev-data` вызывает `engine.prepare_web_test_data()` и создаёт
изолированную Python-compatible копию существующего профиля. Это правильно
для migration/dev, но это не multi-user и не production storage. При явном
`--data-dir` FastAPI работает с указанной локальной папкой. По умолчанию
`create_app()` выбирает test/app data directory через `engine`.

Запрос проходит так:

```text
Vue page/store → frontend/src/api/*.ts → apiRequest/fetch
  → FastAPI router → Services dependency → Python domain service
  → PickleRepository (PKL/JSON; SQLite mirror/cutover helpers могут присутствовать)
  → DTO response → frontend
```

Текущие Web DTO покрывают проекты/этапы/прогресс/папки, заметки и карты,
game, настройки, content/help, documents и Word/Scrivener integrations. Они
являются UI/API compatibility contract, а не cloud sync contract. В частности,
`cover_image` передаётся как data URI (schema допускает до 5 000 000
символов), а не как зашифрованный object-storage объект.

## 3. Текущая структура FastAPI

`backend/app/main.py:create_app()` создаёт `FastAPI`, собирает singleton
`Services` в `app.state`, регистрирует `DomainError` и validation handlers,
`/health`, CORS и шесть router modules под `/api`:

| Router | Назначение и текущая зависимость |
| --- | --- |
| `projects.py` | CRUD проектов, этапов, прогресса, folders, ordering и статистики через `ProjectService`. |
| `notes.py` | Заметки, Mind Elixir payload и XMind import через `ProjectNotesService`. |
| `game.py` | State/catalog/commands через Python `GameService`. |
| `content.py` | Локализация, help/agreement и settings через `ContentService`/`SettingsService`. |
| `integrations.py` | Локальные Word/Scrivener/file-sync операции через `DocumentIntegrationService`. |
| `documents.py` | Документы и external DOCX через `ProjectDocumentService`; часть endpoints использует нестрогие `dict[str, Any]`. |

Все routers обёрнуты `require_session`. Эта dependency сверяет необязательный
общий `X-NFProgress-Token`; когда `NFPROGRESS_SESSION_TOKEN` не задан, она
разрешает любой запрос. Это session guard для прежнего local backend, не
accounts/authentication/authorization и не user isolation.

Для `platform='desktop'` lifespan запускает минутный `_desktop_sync_loop`; в
Web он не стартует. `create_app()` также содержит legacy cutover decisions
для settings/notes/projects/game, зависящие от ownership и
`NFPROGRESS_TAURI_RUNTIME`. Они обслуживают migration/compatibility profiles,
не production cloud.

Наличие сейчас:

- configuration: небольшой `RuntimeConfig` из environment;
- CORS: static default localhost/Tauri/Capacitor origins либо
  `NFPROGRESS_ALLOWED_ORIGINS`;
- handling: `DomainError` и Pydantic 422 в едином JSON envelope;
- logging: стандартный logger, exception logging в desktop loop, Uvicorn
  access log выключен по умолчанию и включается `NFPROGRESS_ACCESS_LOG=1`;
- lifecycle: только optional desktop task; нет production DB lifecycle;
- health: один liveness-style `/health` с application version; readiness DB
  и dependency checks отсутствуют;
- versioning: API version в OpenAPI равен `engine.version`, но URL namespace
  `/api/v1` отсутствует;
- DI: вручную созданный heterogeneous `Services` в `app.state`, без DB session
  scope или repository interface для cloud.

## 4. Текущее хранение и локальная SQLite модель

Web data ownership сейчас принадлежит выбранной локальной папке и Python
compatibility model, а не пользователю cloud account. `PickleRepository` —
прямой backend repository; SQLite может поддерживаться как mirror/cutover
substrate, но для Web profile Projects намеренно остаются pickle-owned. Это
видно и в `Run Web.sh`, и в комментарии `create_app()` о Web compatibility
profile.

Desktop `nfprogress.db` является authoritative для projects/stages/progress,
settings, notes, game и documents. Общие SQL migrations находятся в
`nfprogress/core/sqlite/migrations/001...007`; Rust воспроизводит их в
`frontend/src-tauri/src/sqlite.rs`. Основные структуры:

| Сущность | Идентичность и пригодность |
| --- | --- |
| projects / stages / progress_entries | Строковые stable IDs; legacy generation использует UUID4, а migration repair — deterministic UUID5. Есть `created_at`; projects/stages имеют `updated_at`. |
| notes | Stable string IDs, `updated_at`; canonical payload содержит `created_at`, `updated_at` и incrementing `revision`. |
| documents | Stable string ID и unique `scope_key`; `created_at`, `updated_at`, `revision`; external file bindings отдельно. |
| game_state | Singleton `id=1`, JSON payload и `updated_at`; это агрегат, а не independently syncable objects. |
| project/stage/progress order | Явные `project_order`, `stage_order`, `progress_order`; порядок больше не зависит от rowid. |
| domain_events | Stable `event_id`, status/attempt tracking и processed marker для local Game consumer; это не cloud operation log. |

Связи и нормализованные columns (IDs, parent relations, status, timestamps,
order) пригодны как входные данные для будущего identity mapping. JSON payload
и extension tables помогают сохранить неизвестные поля. Но текущая схема не
является Sync Protocol:

- hard delete выполняется через `DELETE`; persistent tombstones,
  `deleted_at`, delete revision и retention отсутствуют;
- revision есть только в Notes/Documents; нет единообразной entity revision,
  device/actor ID, operation ID, causal metadata или conflict state;
- `updated_at` заполняется не одинаково для всех сущностей и не является
  concurrency contract; clock/source semantics не определены;
- game/settings и расширенные payloads — aggregate JSON, их нельзя без
  отдельного решения построчно переносить в cloud;
- local project IDs не содержат cloud enablement, owner/account relation,
  cloud slot, encrypted envelope или object references.

Следовательно, PostgreSQL нельзя получать механическим переносом SQLite DDL:
локальные FK/cascade/restrict, SQLite JSON/`strftime`, ownership/mirror tables,
single-row game state, локальные filesystem paths и migration provenance имеют
другую семантику. PostgreSQL schema должна сначала моделировать account-owned
cloud metadata и encrypted opaque payloads; она не должна сделать server
authoritative для всех local projects.

## 5. Frontend и platform boundaries

`frontend/src/api/{projects,settings,notes,game,documents,integrations}.ts`
переключают transport: в Tauri используют typed `invoke`/SQLite repositories,
во всех остальных runtime — HTTP. `content.ts` в Tauri отдаёт bundled content,
в Web/mobile — HTTP. Отсюда следует, что frontend уже не жёстко привязан к
Python на Desktop, однако Web/mobile API adapters пока плотно привязаны к
существующим plaintext domain DTO и mutation endpoints.

`frontend/src/platform/runtime.ts` различает Tauri по
`window.__TAURI_INTERNALS__`, Capacitor через `Capacitor.isNativePlatform()` и
иначе Web. Capacitor configuration/Android/iOS wrappers существуют, но не
предоставляют SQLite, secure key storage или queued/offline sync. Документация
сейчас прямо требует для Capacitor remote `VITE_API_BASE_URL`.

`frontend/src-tauri/tauri.conf.json`, Rust commands и
`tests/test_tauri_python_free.py` подтверждают отсутствие production Python
sidecar, local backend health path, localhost session bridge и HTTP fallback
для Tauri project reads. Будущая cloud работа не должна менять это свойство.

## 6. Что можно переиспользовать

- Vue/Ionic routing, stores, locale/content bundling и централизованный
  `apiRequest` error envelope — как presentation/transport foundation.
- Existing Pydantic models и current router contracts — как compatibility
  reference, пока их поведение необходимо Web UI; не как готовые sync DTO.
- FastAPI app factory, router composition, structured domain/validation errors
  и focused API/OpenAPI tests — как основу server packaging.
- Desktop stable IDs, explicit ordering, Notes/Documents revisions, durable
  local game events, shared migration discipline и `rusqlite` repository
  boundary — как local-side prerequisites для будущего Sync Engine.
- Platform detection — как место для явного выбора Web remote transport против
  future mobile local repository; это не готовая mobile persistence layer.

## 7. Dev/migration-only или непригодные для cloud части

- `--dev-data`, `engine.prepare_web_test_data()`, `engine.refresh_test_data()`
  и `Run Web.sh` profile copy — local dev/test adapters.
- `PickleRepository`, PKL/`documents.json`, ownership/cutover flow,
  `SQLiteMirrorRepository` и `NFPROGRESS_TAURI_RUNTIME` logic — migration and
  compatibility machinery, не cloud persistence.
- `--platform desktop` FastAPI lifetime task и local file integrations — не
  должны быть частью normal Tauri runtime или cloud service.
- Existing shared header session token and unauthenticated default are not an
  account security model.
- Local absolute paths, Word/Scrivener inspection, external DOCX bindings and
  base64 cover in project DTO are not cloud storage representations.

## 8. Технический долг и blockers до cloud implementation

1. Нет PostgreSQL driver/connection lifecycle, migration framework, DB schema,
   repository layer или isolated production/dev/test DB configuration.
2. Нет accounts, authentication, authorization, tenant/user ownership,
   registration policy, admin model, quotas or `effective_limit` evaluation.
3. Нет cloud project metadata (`cloud_enabled`, owner, slot accounting), sync
   identity/operation protocol, tombstones/conflict semantics или client queue.
4. Нет client-side crypto/key lifecycle, encrypted envelope/object metadata,
   object storage boundary или cover processing/storage flow.
5. Existing Web service exposes broad plaintext domain data from a local
   profile; its data model cannot safely be treated as shared-server data.
6. API lacks explicit version path and its Documents routes contain untyped
   request dictionaries. These are contract hardening items, not a reason to
   refactor C0 or silently break current Web.
7. Production process assumptions are only Uvicorn CLI plus external HTTPS
   assertion. No deployment config, health/readiness split, secret policy,
   structured observability, rate limiting or production test topology exists.

## 9. Security-sensitive boundaries for later work

- Authentication must use `username + password`; email is only for
  verification/reset. It must replace—not extend as a fallback—the shared
  session-token assumption on protected cloud routes.
- Every cloud query/mutation/object lookup needs server-enforced account
  ownership. Client project UUID is never authorization.
- Future `/admin` must be separately authorized/audited and implement
  OPEN/APPROVAL/CLOSED registration, `max_users`, reserved usernames, block
  state, global defaults and `user_override ?? global_default` limits.
- Protected project contents, document body, notes/maps, cover bytes and sync
  payloads must be opaque ciphertext to backend. Do not log request bodies,
  encryption passphrases, plaintext metadata, tokens or object URLs carrying
  secrets. Account password and encryption passphrase stay separate.
- File/object service must enforce authenticated ownership, content length,
  2 MB post-client-processing cover policy, type/metadata validation and
  bounded uploads; binary covers do not go in PostgreSQL.
- CORS must be explicit per deployed origins; HTTPS, secure session/token
  handling, rate limits (login/reset/upload/admin), safe error responses and
  production access-log policy require separate design and tests.

## 10. PostgreSQL readiness assessment

The backend is structurally reusable as a FastAPI shell, but not ready to
point at PostgreSQL. It has no database abstraction around routers/services,
no async/sync session policy, no migration runner, and current Python services
expect a local mutable compatibility repository. The minimal next step is an
additive production database foundation that leaves current Web compatibility
endpoints operational and clearly separated; it is not a data migration from
local SQLite or PKL.

Recommended production Web/cloud package boundaries:

```text
backend/app/
  main.py                 # composition only
  config.py               # typed, validated runtime environment
  api/                    # versioned cloud routers and DTOs (future)
  db/                     # engine/session lifecycle, migrations integration, readiness
  cloud/                  # account/project-limit/object metadata repositories/services (future)
  legacy_web/             # current Pickle/domain compatibility adapter, isolated
  dependencies.py         # request-scoped dependencies, later auth/authorization
```

Names are a target boundary, not an instruction to move/refactor the current
package during C0. The current six routers must remain available until a later,
explicit compatibility retirement decision.

## 11. Exact scope for C1

C1 is **PostgreSQL production foundation only**. It should be an additive,
reviewable backend task with this contract:

1. Add a typed, validated server configuration separating development, test
   and production and define required PostgreSQL connection environment
   variables without putting secrets in frontend build config.
2. Add the PostgreSQL connection/session lifecycle and one versioned migration
   mechanism. Create only the minimum operational schema needed to prove the
   foundation (schema-version/migration state and health dependency), unless a
   separately approved C1 brief names a minimal non-user domain table.
3. Add DB liveness/readiness checks separate from existing public `/health`;
   failure must be observable and must not silently fall back to
   PickleRepository or local SQLite.
4. Introduce the package seam for future cloud repositories/services while
   preserving current FastAPI router behaviour and current Web dev workflow.
   Explicitly isolate/configure legacy compatibility storage rather than
   pretending it is PostgreSQL-backed.
5. Add focused tests for configuration validation, production/dev/test DB
   isolation, migration upgrade from empty database, connection failure,
   readiness semantics and assurance that legacy Web routes retain their
   existing contract.
6. Document the C1 environment contract and local test procedure. Do not make
   deployment/VPS changes.

Likely affected paths in C1:

- `backend/app/main.py`, `config.py`, `dependencies.py` and a new narrowly
  scoped `backend/app/db/` package;
- a migration directory/tool configuration selected for PostgreSQL;
- `requirements-backend.txt` only for C1's required DB/migration libraries;
- new focused backend tests and a C1 architecture/runbook document;
- possibly a clearly named legacy adapter boundary under `backend/app/`, but
  only if it can be added without moving existing behavior unnecessarily.

## 12. C1 must not change

- No cloud accounts, login, email verification/reset, admin UI/routes or
  registration policy.
- No cloud project enable toggle, quota enforcement, sync protocol/engine,
  local-project limit or server visibility of local-only projects.
- No client-side encryption, passphrase/KDF/KEK/master-key/object-key work and
  no plaintext project-content persistence in the new cloud schema.
- No object storage, cover upload pipeline, binary PostgreSQL cover storage or
  VPS/deployment/infrastructure modification.
- No change to SQLite schema, Desktop Tauri/Rust runtime, Capacitor runtime,
  frontend UI/API behaviour, current legacy API semantics or existing local
  data.
- No refactor or deletion of legacy Python/Pickle migration code; no claim that
  current Web compatibility storage has become production cloud storage.

## 13. C1 Implementation Contract

The next Codex task may use this as its complete starting contract:

> Work only on branch `6.0`. Implement C1 as an additive PostgreSQL backend
> foundation. Preserve the Python-free Tauri Desktop boundary and current
> FastAPI Web compatibility routes. Add typed environment configuration,
> PostgreSQL engine/session lifecycle, one versioned migration path and
> separate database readiness. Keep dev/test/production database targets
> explicitly distinct, ensure DB failures never fall back to PKL/SQLite, and
> add focused automated tests for config, migrations, readiness and regression
> of legacy route contracts. Document required environment variables and local
> verification. Do not add accounts/auth/admin/sync/crypto/object storage,
> cloud project tables/content, UI changes, SQLite migrations, deployment/VPS
> changes or broad refactors.

Before selecting concrete C1 libraries, validate they fit the existing Python
and FastAPI versions and record the decision in the C1 documentation. C1 must
finish with a separate commit, a focused test report, and a diff limited to
the stated backend foundation/docs/tests/dependency manifest scope.
