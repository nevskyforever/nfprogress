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
scp "${SCP_OPTS[@]}" "$SSH_TARGET:$SSH_UPLOAD_DIR/update_manifest.json" update_manifest.json
echo "Manifest download completed."
