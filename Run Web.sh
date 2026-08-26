#!/bin/bash
# Run the unbundled Vue frontend with a Python-compatible developer backend.
set -euo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$SCRIPT_DIR"

case "$MODE" in
  ""|--check) ;;
  *)
    echo "Использование: $0 [--check]"
    exit 2
    ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "Не найден python3."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Не найден npm. Установите Node.js 20.19 или новее."
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "Не найден curl, необходимый для проверки готовности FastAPI."
  exit 1
fi
if ! command -v lsof >/dev/null 2>&1; then
  echo "Не найден lsof, необходимый для проверки локальных портов."
  exit 1
fi
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Не найдены frontend-зависимости. Выполните:"
  echo "  cd frontend && npm ci"
  exit 1
fi

if [ "$MODE" = "--check" ]; then
  echo "Web development prerequisites are ready."
  echo "Backend data: Python-compatible test_data (synchronized at startup)"
  exit 0
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  PORT_PID="$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t | head -n 1)"
  PORT_COMMAND="$(ps -p "$PORT_PID" -o command= 2>/dev/null || true)"
  echo "Порт 8000 уже занят процессом: ${PORT_COMMAND:-PID $PORT_PID}." >&2
  echo "Остановите старый backend и повторите запуск из $ROOT_DIR." >&2
  exit 1
fi
if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  PORT_PID="$(lsof -nP -iTCP:5173 -sTCP:LISTEN -t | head -n 1)"
  PORT_COMMAND="$(ps -p "$PORT_PID" -o command= 2>/dev/null || true)"
  echo "Порт 5173 уже занят процессом: ${PORT_COMMAND:-PID $PORT_PID}." >&2
  echo "Остановите старый frontend и повторите запуск из $ROOT_DIR." >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    pkill -TERM -P "$FRONTEND_PID" >/dev/null 2>&1 || true
    wait "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Запускается FastAPI с тем же test_data, что использует main_UI.py..."
(
  cd "$ROOT_DIR"
  exec python3 -m backend.app \
    --host 127.0.0.1 \
    --port 8000 \
    --platform web \
    --dev-data
) &
BACKEND_PID="$!"

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "FastAPI завершился до готовности."
    exit 1
  fi
  sleep 0.25
done

if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "FastAPI не ответил на /health за 15 секунд."
  exit 1
fi

echo "Откройте http://127.0.0.1:5173"
(
  cd "$ROOT_DIR/frontend"
  exec npm run dev
) &
FRONTEND_PID="$!"
frontend_status=0
wait "$FRONTEND_PID" || frontend_status="$?"
FRONTEND_PID=""
exit "$frontend_status"
