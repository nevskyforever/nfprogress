#!/bin/bash
set -euo pipefail

ARTIFACT_PATH="${1:-}"
REMOTE_NAME="${2:-}"
RELEASES_TO_KEEP="${NFPROGRESS_RELEASES_TO_KEEP:-3}"

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
if [ -n "$REMOTE_NAME" ]; then
  scp "${SCP_OPTS[@]}" "$ARTIFACT_PATH" "$SSH_TARGET:$SSH_UPLOAD_DIR/$REMOTE_NAME"
  UPLOADED_NAME="$REMOTE_NAME"
else
  scp "${SCP_OPTS[@]}" "$ARTIFACT_PATH" "$SSH_TARGET:$SSH_UPLOAD_DIR/"
  UPLOADED_NAME="$(basename "$ARTIFACT_PATH")"
fi

RELEASE_PATTERN=""
case "$UPLOADED_NAME" in
  nfprogress-windows-*.zip)
    RELEASE_PATTERN="nfprogress-windows-*.zip"
    ;;
  nfprogress-mac-arm-*.zip)
    RELEASE_PATTERN="nfprogress-mac-arm-*.zip"
    ;;
  nfprogress-mac-intel-*.zip)
    RELEASE_PATTERN="nfprogress-mac-intel-*.zip"
    ;;
esac

if [ -n "$RELEASE_PATTERN" ]; then
  echo "Keeping latest $RELEASES_TO_KEEP release files matching $RELEASE_PATTERN ..."
  ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "sh -s -- '$SSH_UPLOAD_DIR' '$RELEASE_PATTERN' '$RELEASES_TO_KEEP'" <<'SH'
set -eu

upload_dir=$1
pattern=$2
keep=$3

case "$keep" in
  ''|*[!0-9]*)
    keep=3
    ;;
esac

if [ "$keep" -lt 1 ]; then
  keep=3
fi

cd "$upload_dir" || exit 0

find . -maxdepth 1 -type f -name "$pattern" |
  sed 's#^\./##' |
  sort -V |
  awk -v keep="$keep" '
    { files[NR] = $0 }
    END {
      limit = NR - keep
      for (i = 1; i <= limit; i++) {
        print files[i]
      }
    }
  ' |
  while IFS= read -r old_file; do
    if [ -n "$old_file" ]; then
      rm -f -- "$old_file"
      printf 'Removed old release: %s\n' "$old_file"
    fi
  done
SH
fi
echo "SSH upload completed."
