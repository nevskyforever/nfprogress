# C1 — PostgreSQL foundation для cloud backend

Дата: 2026-09-20. C1 добавляет только server-side инфраструктурную границу
PostgreSQL; это не перенос существующих данных и не cloud-модель.

## Выбранный стек

- `SQLAlchemy>=2.0,<2.1` — зрелый 2.x synchronous engine/session API и
  нормальный connection pool.
- `psycopg[binary]>=3.2,<3.3` — PostgreSQL driver Psycopg 3.
- `alembic>=1.14,<2` — стандартные versioned migrations SQLAlchemy.

Версии совместимы с существующим FastAPI (`>=0.115,<1`) и Pydantic 2 backend.
Используется synchronous SQLAlchemy: текущие FastAPI compatibility handlers и
будущие ранние repository operations не требуют async ORM, а синхронный подход
уменьшает число параллельных DB abstractions. Это не ограничивает будущую
нагрузку, но async SQLAlchemy не добавлен преждевременно.

## Configuration

Конфигурация находится в `backend.app.config.RuntimeConfig`.

| Variable | Meaning |
| --- | --- |
| `NFPROGRESS_ENV` | `development` (default), `test` or `production`. Invalid values stop startup. |
| `NFPROGRESS_DATABASE_URL` | Secret server-only PostgreSQL URL in the exact form `postgresql+psycopg://user:password@host:5432/database`. |

`RuntimeConfig` never includes the database URL in its `repr`; validation
errors do not repeat it. The variable must never be supplied as `VITE_*`, put
in frontend code, committed, logged, or returned by HTTP responses.

In `development` and `test`, the URL is optional. Therefore existing
`Run Web.sh` continues to use the legacy compatibility profile without a cloud
database. `/ready` then returns `503` with `database: not_configured`, which is
intentional and explicit. In `production`, construction of configuration
requires `NFPROGRESS_DATABASE_URL`; SQLite URLs and other drivers are rejected.
No SQLite database is invented by this setting.

## Runtime boundary and lifecycle

`backend/app/db/` is deliberately isolated from `PickleRepository`, desktop
SQLite, local filesystem repositories, and all existing compatibility routers.
At app construction it creates at most one reusable SQLAlchemy `Engine`, with
the normal SQLAlchemy pool and `pool_pre_ping=True`, plus one `sessionmaker`.
Creating the engine does not establish a connection.

Future cloud routes can use `get_cloud_session`: it yields one request-scoped
`Session`, rolls it back on an exception, and always closes it. C1 does not
attach this dependency to any current route and does not introduce business
repositories/models. FastAPI lifespan disposes the reusable engine at shutdown.
Failure to connect has no fallback path to PickleRepository or any SQLite
database.

`GET /health` remains the existing lightweight application liveness endpoint.
`GET /ready` is cloud database readiness:

| State | HTTP | Body |
| --- | --- | --- |
| configured PostgreSQL responds to bounded `SELECT 1` | 200 | `{"status":"ok","database":"ready"}` |
| no cloud database configured | 503 | `{"status":"not_ready","database":"not_configured"}` |
| configured connection cannot be established | 503 | `{"status":"not_ready","database":"unavailable"}` |

The endpoint emits no URL, host, credentials, SQL exception, query text, or
stack trace.

## Alembic

Alembic configuration is `alembic.ini`; it contains no database URL or secret.
`backend/alembic/env.py` obtains the URL only from `RuntimeConfig.from_env()`.
The initial revision `c1_postgresql_foundation` creates no business table.
Alembic itself creates and advances only its standard `alembic_version` state.

Run deployment migrations separately from request startup:

```bash
NFPROGRESS_ENV=production \
NFPROGRESS_DATABASE_URL='postgresql+psycopg://…' \
python -m alembic upgrade head
```

Migrations are never run per request or automatically as a destructive startup
action.

## Local verification

Create an ignored local environment when needed, install the backend manifest
and pytest, then run focused checks:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-backend.txt pytest httpx2
.venv/bin/python -m pytest -q tests/test_cloud_postgresql_foundation.py tests/test_api.py
```

The Alembic integration test requires an explicitly dedicated, disposable real
PostgreSQL database; SQLite is never accepted as a substitute:

```bash
NFPROGRESS_TEST_DATABASE_URL='postgresql+psycopg://…/nfprogress_c1_test' \
.venv/bin/python -m pytest -q \
  tests/test_cloud_postgresql_foundation.py::test_alembic_upgrade_empty_postgresql_database_to_head_twice
```

The test removes only its `alembic_version` table before and after execution,
so that database must contain no application data and be reserved for this test.

## Deliberately not implemented

C1 adds no users, authentication, authorization, quotas, cloud project toggle,
project/content tables, sync/revisions/tombstones, encryption/key material,
object storage/covers, mobile SQLite, frontend changes, Desktop SQLite schema,
Rust/Tauri changes, or legacy PKL migration changes.

## Exact C2 starting contract

C2 may add the first explicitly approved account-owned cloud data model,
authentication/authorization design and cloud-only routers/repositories on top
of `CloudDatabase`, request-scoped sessions, and Alembic. It must keep current
legacy `/api` compatibility endpoints and Desktop local-first SQLite outside
that boundary. C2 must not make PKL/desktop SQLite a fallback for cloud data and
must define ownership, authorization, migrations, and tests before exposing a
new cloud route.
