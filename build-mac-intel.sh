#!/bin/bash
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
echo "Сборка Intel, версия: $VERSION"

if [ -d "build-intel" ]; then
  echo "Очистка старой сборки build-intel..."
  rm -rf build-intel
fi

# Добавляем стандартные переводы Qt для всех языков приложения.
PYSIDE_TRANSLATIONS=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/PySide6/Qt/translations
TRANSLATIONS_TMP=$(mktemp -d)/translations
mkdir -p "$TRANSLATIONS_TMP"
QT_TRANSLATION_LANGUAGES=(ru en es de fr pt_BR)
for QT_LANGUAGE in "${QT_TRANSLATION_LANGUAGES[@]}"; do
  QTBASE_TRANSLATION="$PYSIDE_TRANSLATIONS/qtbase_${QT_LANGUAGE}.qm"
  if [ ! -f "$QTBASE_TRANSLATION" ]; then
    echo "❌ Не найден обязательный перевод Qt: $QTBASE_TRANSLATION"
    rm -rf "$(dirname "$TRANSLATIONS_TMP")"
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
       --macos-target-arch=x86_64 \
       --output-dir=build-intel \
       --include-data-dir="$TRANSLATIONS_TMP=PySide6/Qt/translations" \
       --include-data-dir=mindmap_assets=mindmap_assets \
       --include-data-files=Icon.svg=Icon.svg \
       --lto=yes \
       --disable-ccache \
       --remove-output \
       --prefer-source-code \
       --follow-import-to=engine,game_UI,UI_fiiles \
       --python-flag=-O \
       main_UI.py

# Проверяем успешность сборки
NUITKA_STATUS=$?
rm -rf "$(dirname "$TRANSLATIONS_TMP")"
if [ $NUITKA_STATUS -ne 0 ]; then
  echo "Ошибка сборки Nuitka!"
  exit 1
fi
for QT_LANGUAGE in "${QT_TRANSLATION_LANGUAGES[@]}"; do
  if ! find build-intel -type f -name "qtbase_${QT_LANGUAGE}.qm" -print -quit | grep -q .; then
    echo "❌ Перевод qtbase_${QT_LANGUAGE}.qm не попал в Intel-сборку!"
    exit 1
  fi
done
if ! find build-intel -type f -path "*/mindmap_assets/MindElixir.js" -print -quit | grep -q .; then
  echo "❌ Редактор карт не попал в Intel-сборку!"
  exit 1
fi

# Переходим в папку сборки
cd build-intel

# Переименовываем приложение
if [ -d "main_UI.app" ]; then
  mv main_UI.app nfprogress.app
  echo "✅ Приложение переименовано в nfprogress.app"
else
  echo "❌ Ошибка: main_UI.app не найден!"
  exit 1
fi

# Добавляем лицензию и точную ссылку на исходники внутрь приложения.
APP_RESOURCES="nfprogress.app/Contents/Resources"
SOURCE_REVISION=$(git -C .. rev-parse HEAD)
cp ../LICENSE "$APP_RESOURCES/LICENSE.txt"
cp ../SOURCE_CODE.txt "$APP_RESOURCES/SOURCE_CODE.txt"
{
  printf '\nРевизия сборки: %s\n' "$SOURCE_REVISION"
  printf 'Архив исходного кода: https://github.com/nevskyforever/nfprogress/archive/%s.zip\n' "$SOURCE_REVISION"
} >> "$APP_RESOURCES/SOURCE_CODE.txt"

# Создание DMG установщика
echo "Создание DMG установщика для Intel..."

# Создаем временную папку для DMG
DMG_TEMP="dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Копируем приложение во временную папку
cp -R nfprogress.app "$DMG_TEMP/"
cp "$APP_RESOURCES/LICENSE.txt" "$DMG_TEMP/LICENSE.txt"
cp "$APP_RESOURCES/SOURCE_CODE.txt" "$DMG_TEMP/SOURCE_CODE.txt"

# Создаем символическую ссылку на Applications
ln -s /Applications "$DMG_TEMP/Applications"

# Создаем DMG образ в папке build-intel
DMG_NAME="nfprogress-mac-intel-$VERSION.dmg"
hdiutil create -volname "nfprogress" \
               -srcfolder "$DMG_TEMP" \
               -ov \
               -format UDZO \
               "$DMG_NAME"

# Проверяем создание DMG
if [ $? -eq 0 ] && [ -f "$DMG_NAME" ]; then
  echo "✅ DMG создан: $DMG_NAME"
  echo "Размер DMG: $(ls -lh "$DMG_NAME" | awk '{print $5}')"
else
  echo "❌ Ошибка создания DMG!"
  exit 1
fi

# Очищаем временную папку
rm -rf "$DMG_TEMP"

# Создаем ZIP архив с DMG
echo "Создание ZIP архива..."
zip -r "nfprogress-mac-intel-$VERSION.zip" "$DMG_NAME"

# Удаляем .app и .dmg после создания ZIP
echo "Очистка временных файлов..."
rm -rf nfprogress.app
rm -f "$DMG_NAME"

# Возвращаемся в корневую папку
cd ..

echo "========================================="
echo "✅ Сборка завершена успешно!"
echo "Версия: $VERSION"
echo ""
echo "📦 Итоговый файл:"
if [ -f "build-intel/nfprogress-mac-intel-$VERSION.zip" ]; then
  echo "   ZIP: build-intel/nfprogress-mac-intel-$VERSION.zip ($(ls -lh build-intel/nfprogress-mac-intel-$VERSION.zip | awk '{print $5}'))"
fi
echo "========================================="

./scripts/upload-release.sh "build-intel/nfprogress-mac-intel-$VERSION.zip"

if [ "${NFPROGRESS_DEFER_MANIFEST:-0}" != "1" ]; then
  ./scripts/download-release-manifest.sh
  python3 scripts/update-release-manifest.py "$VERSION" macos_intel
  ./scripts/upload-release.sh "update_manifest.json"
  python3 scripts/create-legacy-manifest.py
  SSH_UPLOAD_DIR="nfproject/public_html" ./scripts/upload-release.sh "update_manifest_legacy.json" "update_manifest.json"
fi
