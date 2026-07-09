#!/bin/bash
set -euo pipefail

ARTIFACT_PATH="${1:-}"

SSH_UPLOAD_HOST="${SSH_UPLOAD_HOST:-77.222.62.219}"
SSH_UPLOAD_USER="${SSH_UPLOAD_USER:-nevskyfore}"
SSH_UPLOAD_DIR="${SSH_UPLOAD_DIR:-nfproject/public_html/app}"
SSH_UPLOAD_PORT="${SSH_UPLOAD_PORT:-22}"
if [ -z "${SSH_UPLOAD_KEY_PATH:-}" ] && [ -f "$HOME/.ssh/nfprogress_spaceweb" ]; then
  SSH_UPLOAD_KEY_PATH="$HOME/.ssh/nfprogress_spaceweb"
fi

if [ -z "$ARTIFACT_PATH" ]; then
  echo "SSH upload skipped: artifact path is empty."
  exit 0
fi

if [ ! -f "$ARTIFACT_PATH" ]; then
  echo "SSH upload skipped: artifact not found: $ARTIFACT_PATH"
  exit 0
fi

if [ -z "$SSH_UPLOAD_HOST" ] || [ -z "$SSH_UPLOAD_USER" ] || [ -z "$SSH_UPLOAD_DIR" ]; then
  echo "SSH upload skipped: set SSH_UPLOAD_HOST, SSH_UPLOAD_USER and SSH_UPLOAD_DIR to enable it."
  exit 0
fi

SSH_TARGET="${SSH_UPLOAD_USER}@${SSH_UPLOAD_HOST}"
SSH_OPTS=(-p "$SSH_UPLOAD_PORT")
SCP_OPTS=(-P "$SSH_UPLOAD_PORT")

if [ -n "${SSH_UPLOAD_KEY_PATH:-}" ]; then
  SSH_OPTS+=(-i "$SSH_UPLOAD_KEY_PATH")
  SCP_OPTS+=(-i "$SSH_UPLOAD_KEY_PATH")
fi

echo "Uploading $(basename "$ARTIFACT_PATH") to $SSH_TARGET:$SSH_UPLOAD_DIR ..."
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "mkdir -p '$SSH_UPLOAD_DIR'"
scp "${SCP_OPTS[@]}" "$ARTIFACT_PATH" "$SSH_TARGET:$SSH_UPLOAD_DIR/"
echo "SSH upload completed."
