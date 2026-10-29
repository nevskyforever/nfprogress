#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:-quick}"
container_name=""
test_dsn=""

usage() {
  printf 'Usage: %s {quick|backend|frontend|prepush}\n' "${0##*/}"
}

step() {
  local label="$1"
  shift
  printf '\n[RUN] %s\n' "$label"
  "$@"
  printf '[PASS] %s\n' "$label"
}

cleanup_postgres() {
  [[ -n "$container_name" ]] || return 0
  if ! docker inspect "$container_name" >/dev/null 2>&1; then
    return 0
  fi
  local labels image
  labels="$(docker inspect --format '{{ index .Config.Labels "worta.local-acceptance" }}' "$container_name")"
  image="$(docker inspect --format '{{.Config.Image}}' "$container_name")"
  if [[ "$labels" == 1 && "$image" == postgres:16 ]]; then
    docker stop "$container_name" >/dev/null
    printf '[PASS] stopped task-owned PostgreSQL container %s\n' "$container_name"
  else
    printf '[FAIL] refusing to stop an unverified Docker container: %s\n' "$container_name" >&2
    return 1
  fi
}

trap cleanup_postgres EXIT
trap 'exit 130' INT TERM

start_postgres() {
  command -v docker >/dev/null || { printf '[NOT RUN] Docker is unavailable.\n' >&2; return 1; }
  docker info >/dev/null || { printf '[NOT RUN] Docker Engine is unavailable.\n' >&2; return 1; }

  local suffix password mapped_port
  suffix="$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
  password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  container_name="worta-local-acceptance-${suffix}"

  POSTGRES_PASSWORD="$password" docker run --rm -d \
    --name "$container_name" \
    --label worta.local-acceptance=1 \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_DB=worta_local_test \
    -e POSTGRES_PASSWORD \
    -p 127.0.0.1::5432 \
    postgres:16 >/dev/null
  local ready=0
  for _attempt in {1..45}; do
    if docker exec "$container_name" pg_isready -U postgres -d worta_local_test >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    printf '[FAIL] task-owned PostgreSQL 16 did not become ready.\n' >&2
    return 1
  fi

  mapped_port="$(docker port "$container_name" 5432/tcp | awk -F: '/^127\.0\.0\.1:/ {print $NF}')"
  [[ "$mapped_port" =~ ^[0-9]+$ ]] || {
    printf '[FAIL] test database port is not bound to IPv4 loopback.\n' >&2
    return 1
  }
  test_dsn="postgresql+psycopg://postgres:${password}@127.0.0.1:${mapped_port}/worta_local_test"
  unset password
  export NFPROGRESS_TEST_DATABASE_URL="$test_dsn"
  export NFPROGRESS_ENV=test
  export PYTHONDONTWRITEBYTECODE=1
  unset POSTGRES_PASSWORD
  printf '[PASS] isolated PostgreSQL 16 is ready on 127.0.0.1:%s (DSN hidden)\n' "$mapped_port"
}

quick_checks() {
  cd "$repo_root"
  git diff --check
  local changed_file
  while IFS= read -r changed_file; do
    [[ "$changed_file" == *.py ]] || continue
    python3 - "$changed_file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
compile(path.read_text(encoding='utf-8'), str(path), 'exec')
PY
  done < <({ git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u)
  bash -n scripts/maintenance/local_acceptance.sh scripts/maintenance/run_cloud_restore_preflight.sh
  python3 - <<'PY'
from pathlib import Path
import yaml

for path in Path('.github/workflows').glob('*.yml'):
    yaml.safe_load(path.read_text(encoding='utf-8'))
print('workflow YAML: PASS')
PY
}

backend_checks() {
  cd "$repo_root"
  start_postgres
  python3 -m pytest -q \
    tests/test_cloud_c18_cover_gate.py \
    tests/test_cloud_c18_compression_gate.py \
    tests/test_cloud_c18_game_gate.py \
    tests/test_cloud_c18_map_gate.py \
    tests/test_cloud_c18_document_gate.py \
    tests/test_cloud_c18_progress_gate.py \
    tests/test_cloud_postgresql_foundation.py \
    tests/test_cloud_resource_limits.py \
    tests/test_backend_production_boundary.py \
    tests/test_cloud_auth.py \
    tests/test_cloud_email_recovery.py \
    tests/test_cloud_registration.py \
    tests/test_cloud_limits.py \
    tests/test_cloud_reserved_usernames.py \
    tests/test_cloud_admin.py \
    tests/test_cloud_invitations.py \
    tests/test_cloud_legal_acceptance.py \
    tests/test_cloud_projects.py \
    tests/test_web_cloud_read.py \
    tests/test_web_replay.py \
    tests/test_web_replay_metadata.py \
    tests/test_web_replay_structural.py \
    tests/test_web_replay_source_seed.py \
    tests/test_cloud_encrypted_schema.py \
    tests/test_cloud_encrypted_sync.py \
    tests/test_cloud_encrypted_sync_v2.py \
    tests/test_cloud_encrypted_blobs.py \
    tests/test_c9_sqlite_sync.py \
    tests/test_api.py \
    tests/test_c18_external_local_boundary.py \
    tests/test_c18_compression_distribution.py

  step 'real disposable PostgreSQL and encrypted-blob backup/restore' \
    bash scripts/maintenance/run_cloud_restore_preflight.sh
}

frontend_checks() {
  cd "$repo_root/frontend"
  npm test -- --run \
    src/api/cloudProjects.spec.ts \
    src/platform/web/cloudRead.spec.ts \
    src/platform/web/replayReceiver.spec.ts \
    src/platform/web/replayStructural.spec.ts \
    src/platform/web/replayContentUpdate.spec.ts \
    src/platform/web/replaySourceSeed.spec.ts \
    src/platform/web/stageApply.spec.ts \
    src/platform/web/stageOrderApply.spec.ts \
    src/platform/web/stagePrefix.spec.ts \
    src/platform/web/stageOrderPrefix.spec.ts \
    src/platform/web/importedMetadataApply.spec.ts \
    src/platform/web/importedMetadataMigration.spec.ts \
    src/platform/web/metadataPrefixProof.spec.ts \
    src/platform/web/projectBindings.spec.ts \
    src/platform/web/syncDurability.spec.ts \
    src/cloud/projectMetadataMigrationRuntime.spec.ts \
    src/platform/web/cloudAccountSession.spec.ts \
    src/components/settings/BrowserCloudAccountCard.spec.ts \
    src/platform/web/localDocuments.spec.ts \
    src/platform/web/localAuthority.spec.ts \
    src/cloud/documentCodec.spec.ts \
    src/platform/web/v10MixedRecovery.spec.ts \
    src/platform/web/postFMetadataBoundary.spec.ts \
    src/platform/web/historicalMetadataDependency.spec.ts \
    src/platform/web/historicalContentAuthentication.spec.ts \
    src/platform/web/historicalPrefixQualification.spec.ts \
    src/platform/web/postFMetadataRecovery.spec.ts \
    src/platform/web/privateMetadataPrefix.spec.ts \
    src/platform/web/legacy3Prefix.spec.ts \
    src/platform/web/legacy3OrdinaryPrefix.spec.ts \
    --maxWorkers=1
  npm run typecheck
  npm run build

  npx playwright install chromium
  local log_file server_pid ready=0
  log_file="$(mktemp -t worta-local-acceptance-vite.XXXXXX)"
  ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort >"$log_file" 2>&1 &
  server_pid=$!
  cleanup_vite() {
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" 2>/dev/null || true
    rm -f "$log_file"
  }
  for _attempt in {1..45}; do
    if curl --fail --silent http://127.0.0.1:5173/scripts/browser-cloud-account-harness.html >/dev/null; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    printf '[FAIL] local Vite harness did not become ready.\n' >&2
    tail -n 80 "$log_file" >&2
    cleanup_vite
    return 1
  fi
  node scripts/browser-local-stages-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  node scripts/browser-cloud-account-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  node scripts/browser-encrypted-workspace-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  node scripts/browser-local-documents-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  node scripts/browser-local-document-migration-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  node scripts/browser-replay-storage-acceptance.mjs http://127.0.0.1:5173 || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  WORTA_CONTENT_CHROMIUM=1 npm exec vitest run src/platform/web/replayContentUpdate.spec.ts || {
    local status=$?
    cleanup_vite
    return "$status"
  }
  cleanup_vite
}

case "$mode" in
  quick)
    step 'diff, changed Python syntax, shell syntax, and workflow YAML' quick_checks
    ;;
  backend)
    step 'PostgreSQL migration and backend regression acceptance' backend_checks
    ;;
  frontend)
    step 'frontend Vitest, typecheck, build, and Chromium acceptance' frontend_checks
    ;;
  prepush)
    step 'quick static checks' quick_checks
    step 'frontend local acceptance' frontend_checks
    step 'PostgreSQL backend and backup/restore acceptance' backend_checks
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
