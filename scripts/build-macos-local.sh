#!/bin/bash
set -euo pipefail

ARCH="${1:-}"
case "$ARCH" in
  arm) BUILD_DIR="build-arm"; TARGET_ARCH=""; ARCH_LABEL="ARM"; ARTIFACT_PREFIX="nfprogress-mac-arm" ;;
  intel) BUILD_DIR="build-intel"; TARGET_ARCH="--macos-target-arch=x86_64"; ARCH_LABEL="Intel"; ARTIFACT_PREFIX="nfprogress-mac-intel" ;;
  *) echo "Использование: $0 arm|intel"; exit 2 ;;
esac

cd "$(dirname "$0")/.."
BUILD_LOCK_DIR="${TMPDIR:-/tmp}/nfprogress-${ARCH}-build-${UID}.lock"
if ! mkdir "$BUILD_LOCK_DIR" 2>/dev/null; then
  echo "Ошибка: $ARCH_LABEL-сборка уже выполняется. Дождитесь её завершения."
  exit 1
fi
trap 'rmdir "$BUILD_LOCK_DIR" 2>/dev/null || true' EXIT
if pgrep -f "[n]uitka.*--output-dir=$BUILD_DIR" >/dev/null; then
  echo "Ошибка: $ARCH_LABEL-сборка уже выполняется. Дождитесь её завершения."
  exit 1
fi

MIN_NUITKA_VERSION=4.1.3
if ! python3 - "$MIN_NUITKA_VERSION" <<'PY'
import sys

try:
    from nuitka.Version import getNuitkaVersion
    current = tuple(int(part) for part in getNuitkaVersion().split('.')[:3])
    required = tuple(int(part) for part in sys.argv[1].split('.'))
except (ImportError, ValueError):
    raise SystemExit(1)
raise SystemExit(0 if current >= required else 1)
PY
then
  echo "Ошибка: для сборки требуется Nuitka $MIN_NUITKA_VERSION или новее."
  echo "Обновите Nuitka: python3 -m pip install --upgrade 'Nuitka>=$MIN_NUITKA_VERSION'"
  exit 1
fi

VERSION=$(python3 -c "import engine; print(engine.version)")
echo "Локальная сборка $ARCH_LABEL, версия: $VERSION"
if [ -d "$BUILD_DIR" ]; then
  echo "Очистка старой сборки $BUILD_DIR..."
  rm -rf "$BUILD_DIR"
fi

PYSIDE_TRANSLATIONS=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/PySide6/Qt/translations
TRANSLATIONS_TMP=$(mktemp -d)/translations
mkdir -p "$TRANSLATIONS_TMP"
trap 'rm -rf "$(dirname "$TRANSLATIONS_TMP")"; rmdir "$BUILD_LOCK_DIR" 2>/dev/null || true' EXIT
QT_TRANSLATION_LANGUAGES=(ru en es de fr pt_BR)
for QT_LANGUAGE in "${QT_TRANSLATION_LANGUAGES[@]}"; do
  QTBASE_TRANSLATION="$PYSIDE_TRANSLATIONS/qtbase_${QT_LANGUAGE}.qm"
  if [ ! -f "$QTBASE_TRANSLATION" ]; then
    echo "❌ Не найден обязательный перевод Qt: $QTBASE_TRANSLATION"
    exit 1
  fi
  cp "$PYSIDE_TRANSLATIONS"/*_"$QT_LANGUAGE".qm "$TRANSLATIONS_TMP"/
done

python3 -m nuitka --standalone \
       --macos-create-app-bundle \
       --macos-app-icon=appIcon.icns \
       --macos-app-name="nfprogress" \
       --macos-app-version="$VERSION" \
       --company-name="nfproject" \
       --file-description="Трекер для писателей" \
       --enable-plugin=pyside6 \
       --include-qt-plugins=qml,webview \
       --noinclude-dlls='*QtWebEngine*' \
       --noinclude-dlls='*qtwebengine*' \
       --noinclude-dlls='*qtwebview_webengine*' \
       --noinclude-dlls='*qtquickshapesdesignhelpersplugin*' \
       --noinclude-dlls='PySide6/qml/QtQuick/Shapes/DesignHelpers/*' \
       $TARGET_ARCH \
       --output-dir="$BUILD_DIR" \
       --include-data-dir="$TRANSLATIONS_TMP=PySide6/Qt/translations" \
       --include-data-dir=mindmap_assets=mindmap_assets \
       --include-data-dir=notes_assets=notes_assets \
       --include-data-files=Icon.svg=Icon.svg \
       --lto=yes --disable-ccache --remove-output --prefer-source-code \
       --follow-import-to=engine,game_UI,UI_fiiles --python-flag=-O main_UI.py

rm -rf "$(dirname "$TRANSLATIONS_TMP")"
for QT_LANGUAGE in "${QT_TRANSLATION_LANGUAGES[@]}"; do
  if ! find "$BUILD_DIR" -type f -name "qtbase_${QT_LANGUAGE}.qm" -print -quit | grep -q .; then
    echo "❌ Перевод qtbase_${QT_LANGUAGE}.qm не попал в $ARCH_LABEL-сборку!"
    exit 1
  fi
done
if ! find "$BUILD_DIR" -type f -path '*/mindmap_assets/MindElixir.js' -print -quit | grep -q .; then
  echo "❌ Редактор карт не попал в $ARCH_LABEL-сборку!"
  exit 1
fi
if ! find "$BUILD_DIR" -type f -path '*/notes_assets/vendor/muuri.min.js' -print -quit | grep -q .; then
  echo "❌ Редактор заметок не попал в $ARCH_LABEL-сборку!"
  exit 1
fi

cd "$BUILD_DIR"
if [ -d main_UI.app ]; then mv main_UI.app nfprogress.app; else echo "❌ Ошибка: main_UI.app не найден!"; exit 1; fi
APP_RESOURCES="nfprogress.app/Contents/Resources"
SOURCE_REVISION=$(git -C .. rev-parse HEAD)
cp ../LICENSE "$APP_RESOURCES/LICENSE.txt"
cp ../SOURCE_CODE.txt "$APP_RESOURCES/SOURCE_CODE.txt"
{
  printf '\nРевизия сборки: %s\n' "$SOURCE_REVISION"
  printf 'Архив исходного кода: https://github.com/nevskyforever/nfprogress/archive/%s.zip\n' "$SOURCE_REVISION"
} >> "$APP_RESOURCES/SOURCE_CODE.txt"

DMG_TEMP=dmg_temp
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"
cp -R nfprogress.app "$DMG_TEMP/"
cp "$APP_RESOURCES/LICENSE.txt" "$DMG_TEMP/LICENSE.txt"
cp "$APP_RESOURCES/SOURCE_CODE.txt" "$DMG_TEMP/SOURCE_CODE.txt"
ln -s /Applications "$DMG_TEMP/Applications"
DMG_NAME="$ARTIFACT_PREFIX-$VERSION.dmg"
hdiutil create -volname nfprogress -srcfolder "$DMG_TEMP" -ov -format UDZO "$DMG_NAME"
rm -rf "$DMG_TEMP"
zip -r "$ARTIFACT_PREFIX-$VERSION.zip" "$DMG_NAME"
rm -rf nfprogress.app "$DMG_NAME"
cd ..
echo "✅ Локальная сборка завершена: $BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"
