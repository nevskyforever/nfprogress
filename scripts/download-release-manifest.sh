#!/bin/bash
set -euo pipefail

SSH_UPLOAD_HOST="${SSH_UPLOAD_HOST:-77.222.62.219}"
SSH_UPLOAD_USER="${SSH_UPLOAD_USER:-nevskyfore}"
SSH_UPLOAD_DIR="${SSH_UPLOAD_DIR:-nfproject/public_html/app}"
SSH_UPLOAD_PORT="${SSH_UPLOAD_PORT:-22}"
if [ -z "${SSH_UPLOAD_KEY_PATH:-}" ] && [ -f "$HOME/.ssh/nfprogress_spaceweb" ]; then
  SSH_UPLOAD_KEY_PATH="$HOME/.ssh/nfprogress_spaceweb"
fi

SSH_TARGET="${SSH_UPLOAD_USER}@${SSH_UPLOAD_HOST}"
SCP_OPTS=(-P "$SSH_UPLOAD_PORT")

if [ -n "${SSH_UPLOAD_KEY_PATH:-}" ]; then
  SCP_OPTS+=(-i "$SSH_UPLOAD_KEY_PATH")
fi

echo "Downloading current update_manifest.json from $SSH_TARGET:$SSH_UPLOAD_DIR ..."
LOCAL_NOTES_FILE=$(mktemp)
python3 - "$LOCAL_NOTES_FILE" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path("update_manifest.json")
if not manifest_path.exists():
    raise SystemExit(0)

try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

notes = manifest.get("notes")
if notes is not None:
    Path(sys.argv[1]).write_text(str(notes), encoding="utf-8")
PY

scp "${SCP_OPTS[@]}" "$SSH_TARGET:$SSH_UPLOAD_DIR/update_manifest.json" update_manifest.json

if [ -s "$LOCAL_NOTES_FILE" ]; then
  python3 - "$LOCAL_NOTES_FILE" <<'PY'
import json
import sys
from pathlib import Path

notes = Path(sys.argv[1]).read_text(encoding="utf-8")
manifest_path = Path("update_manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["notes"] = notes
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
fi
rm -f "$LOCAL_NOTES_FILE"
echo "Manifest download completed."
