#!/bin/bash
VERSION=$(python3 -c "import engine; print(engine.version)")
echo "Сборка ARM, версия: $VERSION"

if [ -d "build-arm" ]; then
  echo "Очистка старой сборки build-arm..."
  rm -rf build-arm
fi

rm -rf app_translations
mkdir app_translations
PYSIDE_TRANS_DIR=$(python3 -c "import sys; from PySide6.QtCore import QLibraryInfo; sys.stdout.write(QLibraryInfo.path(QLibraryInfo.TranslationsPath))")
cp "$PYSIDE_TRANS_DIR/qt_ru.qm" app_translations/
cp "$PYSIDE_TRANS_DIR/qtbase_ru.qm" app_translations/
cp "$PYSIDE_TRANS_DIR/qt_en.qm" app_translations/
cp "$PYSIDE_TRANS_DIR/qtbase_en.qm" app_translations/

nuitka --standalone \
       --macos-create-app-bundle \
       --macos-app-icon=appIcon.icns \
       --macos-app-name="nfprogress" \
       --macos-app-version="$VERSION" \
       --company-name="nfproject" \
       --file-description="Трекер для писателей" \
       --enable-plugin=pyside6 \
       --output-dir=build-arm \
       --include-data-dir=app_translations=translations \
       --lto=yes \
       --disable-ccache \
       --remove-output \
       --prefer-source-code \
       --follow-import-to=engine,game_UI,UI_fiiles \
       --python-flag=-O \
       main_UI.py

# Проверяем успешность сборки
if [ $? -ne 0 ]; then
  echo "Ошибка сборки Nuitka!"
  exit 1
fi

# Переходим в папку сборки
cd build-arm

# Переименовываем приложение
if [ -d "main_UI.app" ]; then
  mv main_UI.app nfprogress.app
  echo "✅ Приложение переименовано в nfprogress.app"
else
  echo "❌ Ошибка: main_UI.app не найден!"
  exit 1
fi

# Создание DMG установщика
echo "Создание DMG установщика для ARM..."

# Создаем временную папку для DMG
DMG_TEMP="dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Копируем приложение во временную папку
cp -R nfprogress.app "$DMG_TEMP/"

# Создаем символическую ссылку на Applications
ln -s /Applications "$DMG_TEMP/Applications"

# Создаем DMG образ в папке build-arm
DMG_NAME="nfprogress-mac-arm-$VERSION.dmg"
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
zip -r "nfprogress-mac-arm-$VERSION.zip" "$DMG_NAME"

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
if [ -f "build-arm/nfprogress-mac-arm-$VERSION.zip" ]; then
  echo "   ZIP: build-arm/nfprogress-mac-arm-$VERSION.zip ($(ls -lh build-arm/nfprogress-mac-arm-$VERSION.zip | awk '{print $5}'))"
fi
echo "========================================="