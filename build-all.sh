#!/bin/bash
set +e

VERSION=$(python3 -c "import engine; print(engine.version)")
MANIFEST_STATUS=0

RELEASE_NOTES=$(git log -1 --format=%B | awk '
  /^[[:space:]]*Обновление[[:space:]]+[0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ {
    found = 1
    next
  }
  found && !started && /^[[:space:]]*$/ {
    next
  }
  found {
    started = 1
    print
  }
')

if [ -n "$RELEASE_NOTES" ]; then
  export RELEASE_NOTES
  echo "Описание обновления извлечено из последнего коммита."
else
  unset RELEASE_NOTES
  echo "Описание обновления в последнем коммите не найдено."
fi

echo "Запуск параллельной сборки ARM и Intel..."

NFPROGRESS_DEFER_MANIFEST=1 ./build-mac-arm.sh &
ARM_PID=$!

NFPROGRESS_DEFER_MANIFEST=1 ./build-mac-intel.sh &
INTEL_PID=$!

wait "$ARM_PID"
ARM_STATUS=$?

wait "$INTEL_PID"
INTEL_STATUS=$?

if [ $ARM_STATUS -eq 0 ] || [ $INTEL_STATUS -eq 0 ]; then
  ./scripts/download-release-manifest.sh || MANIFEST_STATUS=1
fi

if [ $ARM_STATUS -ne 0 ]; then
  echo "❌ ARM сборка или загрузка завершилась с ошибкой, manifest для ARM не обновлен."
elif [ $MANIFEST_STATUS -eq 0 ]; then
  python3 scripts/update-release-manifest.py "$VERSION" macos_arm || MANIFEST_STATUS=1
fi

if [ $INTEL_STATUS -ne 0 ]; then
  echo "❌ Intel сборка или загрузка завершилась с ошибкой, manifest для Intel не обновлен."
elif [ $MANIFEST_STATUS -eq 0 ]; then
  python3 scripts/update-release-manifest.py "$VERSION" macos_intel || MANIFEST_STATUS=1
fi

if [ $ARM_STATUS -eq 0 ] || [ $INTEL_STATUS -eq 0 ]; then
  ./scripts/upload-release.sh "update_manifest.json" || MANIFEST_STATUS=1
  python3 scripts/create-legacy-manifest.py || MANIFEST_STATUS=1
  SSH_UPLOAD_DIR="nfproject/public_html" ./scripts/upload-release.sh "update_manifest_legacy.json" "update_manifest.json" || MANIFEST_STATUS=1
fi

if [ $ARM_STATUS -ne 0 ] || [ $INTEL_STATUS -ne 0 ] || [ $MANIFEST_STATUS -ne 0 ]; then
  echo "❌ Одна или несколько сборок завершились с ошибкой."
  exit 1
fi

echo "Обе сборки и загрузка manifest завершены!"
