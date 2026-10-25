#!/usr/bin/env bash
set -euo pipefail

# Entirely local, opt-in, and disposable. No VPS or configured application DB.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
container_name="worta-mvp607-restore-$$"
started=0

cleanup() {
  if [[ "$started" == 1 ]]; then
    docker stop "$container_name" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export POSTGRES_PASSWORD
docker run --rm -d \
  --name "$container_name" \
  --label worta.restore-test=1 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -e POSTGRES_PASSWORD \
  -p 127.0.0.1::5432 \
  postgres:16 >/dev/null
started=1
unset POSTGRES_PASSWORD

ready=0
for _attempt in {1..30}; do
  if docker exec "$container_name" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  echo 'Disposable PostgreSQL did not become ready.' >&2
  exit 1
fi

cd "$repo_root"
NFPROGRESS_RESTORE_TEST_CONTAINER="$container_name" \
  PYTHONDONTWRITEBYTECODE=1 \
  python3 -m pytest -q tests/test_cloud_backup_restore_readiness.py
