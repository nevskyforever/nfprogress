#!/usr/bin/env bash
# Disposable local-only server and Desktop profiles for manual acceptance.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:-}"
case "$mode" in
  server)
    if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
      printf 'Port 8000 is occupied; stop only a verified test process before retrying.\n' >&2
      exit 1
    fi
    docker info >/dev/null
    test_root="$(mktemp -d "${TMPDIR:-/tmp}/worta-desktop-smoke.XXXXXXXX")"
    touch "$test_root/.worta-desktop-smoke"
    mkdir "$test_root/server" "$test_root/A" "$test_root/B"
    name="worta-smoke-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
    password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    server_pid=""
    cleanup() {
      if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
        kill -CONT "$server_pid" 2>/dev/null || true
        kill -TERM "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
      fi
      if docker inspect --format '{{ index .Config.Labels "worta.desktop-smoke" }}' "$name" 2>/dev/null | grep -qx 1; then
        docker stop "$name" >/dev/null
      fi
    }
    trap cleanup EXIT
    trap 'exit 130' INT TERM
    POSTGRES_PASSWORD="$password" docker run --rm -d --name "$name" --label worta.desktop-smoke=1 \
      -e POSTGRES_USER=postgres -e POSTGRES_DB=worta_smoke -e POSTGRES_PASSWORD \
      -p 127.0.0.1::5432 postgres:16 >/dev/null
    ready=0
    for _ in {1..45}; do
      if docker exec "$name" pg_isready -U postgres -d worta_smoke >/dev/null 2>&1; then ready=1; break; fi
      sleep 1
    done
    [[ "$ready" == 1 ]] || { printf 'PostgreSQL did not start.\n' >&2; exit 1; }
    port="$(docker port "$name" 5432/tcp | awk -F: '/^127\.0\.0\.1:/ {print $NF}')"
    [[ "$port" =~ ^[0-9]+$ ]] || exit 1
    export NFPROGRESS_DATABASE_URL="postgresql+psycopg://postgres:${password}@127.0.0.1:${port}/worta_smoke"
    unset password POSTGRES_PASSWORD
    export NFPROGRESS_ENV=test NFPROGRESS_DATA_DIR="$test_root/server" PYTHONDONTWRITEBYTECODE=1
    export NFPROGRESS_AUTH_SECRET='disposable-local-smoke-secret-at-least-32-characters'
    export NFPROGRESS_PUBLIC_WEB_URL='https://app.example.test'
    cd "$repo_root"
    python3 -m alembic upgrade head
    python3 - <<'PY'
import os
import sys
from sqlalchemy import create_engine
sys.path.insert(0, 'tests')
from test_cloud_auth import create_user
engine = create_engine(os.environ['NFPROGRESS_DATABASE_URL'])
try:
    create_user(engine, username='MvpSmoke', email='mvp-smoke@example.test', password='isolated-smoke-password')
finally:
    engine.dispose()
PY
    printf '\nDisposable test root: %s\nTest account: MvpSmoke / isolated-smoke-password\n' "$test_root"
    printf 'The database is removed when this server command exits; the profile files are retained.\n'
    python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
    server_pid=$!
    printf '%s\n' "$server_pid" > "$test_root/server.pid"
    wait "$server_pid"
    ;;
  client)
    test_root="${2:-}"; profile="${3:-}"
    [[ -f "$test_root/.worta-desktop-smoke" && ( "$profile" == A || "$profile" == B ) ]] || {
      printf 'Usage: %s client TEST_ROOT A|B\n' "$0" >&2; exit 2;
    }
    if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
      printf 'Port 5173 is occupied; use the existing smoke Vite server only after verifying its project path.\n' >&2
      exit 1
    fi
    cd "$repo_root/frontend"
    NFPROGRESS_BUILD_PROFILE=test NFPROGRESS_DATA_DIR="$test_root/$profile" \
      CARGO_INCREMENTAL=0 CARGO_BUILD_JOBS=2 exec npm run tauri:dev
    ;;
  *) printf 'Usage: %s server | client TEST_ROOT A|B\n' "$0" >&2; exit 2 ;;
esac
