#!/bin/bash
VERSION=$(python3 -c "import engine; print(engine.version)")
echo "Сборка Intel, версия: $VERSION"

python3 scripts/update-release-manifest.py "$VERSION"

if [ -d "build-intel" ]; then
  echo "Очистка старой сборки build-intel..."
  rm -rf build-intel
fi

# Оставляем только .qm-файлы для ru/en: QTranslator подгружает qt_ru.qm
# вместе со всеми его подкаталогами (qtbase_ru.qm и т.д.) из той же папки,
# поэтому нельзя брать один произвольный файл - нужны все *_ru.qm/*_en.qm.
PYSIDE_TRANSLATIONS=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/PySide6/Qt/translations
TRANSLATIONS_TMP=$(mktemp -d)/translations
mkdir -p "$TRANSLATIONS_TMP"
cp "$PYSIDE_TRANSLATIONS"/*_ru.qm "$PYSIDE_TRANSLATIONS"/*_en.qm "$TRANSLATIONS_TMP"/

nuitka --standalone \
       --macos-create-app-bundle \
       --macos-app-icon=appIcon.icns \
       --macos-app-name="nfprogress" \
       --macos-app-version="$VERSION" \
       --company-name="nfproject" \
       --file-description="Трекер для писателей" \
       --enable-plugin=pyside6 \
       --macos-target-arch=x86_64 \
       --output-dir=build-intel \
       --include-data-dir="$TRANSLATIONS_TMP=PySide6/Qt/translations" \
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

# Создание DMG установщика
echo "Создание DMG установщика для Intel..."

# Создаем временную папку для DMG
DMG_TEMP="dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Копируем приложение во временную папку
cp -R nfprogress.app "$DMG_TEMP/"

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
./scripts/upload-release.sh "update_manifest.json"
SSH_UPLOAD_DIR="nfproject/public_html" ./scripts/upload-release.sh "update_manifest.json"
