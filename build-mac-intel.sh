#!/bin/bash
VERSION=$(python3 -c "import engine; print(engine.version)")
echo "Сборка Intel, версия: $VERSION"

if [ -d "build-intel" ]; then
  echo "Очистка старой сборки build-intel..."
  rm -rf build-intel
fi

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
       --include-data-dir=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/PySide6/Qt/translations=PySide6/Qt/translations \
       --lto=yes \
       --disable-ccache \
       --remove-output \
       --prefer-source-code \
       --follow-import-to=engine,game_UI,UI_fiiles \
       --python-flag=-O \
       main_UI.py && \
cd build-intel && mv main_UI.app nfprogress.app && zip -r nfprogress-mac-intel-$VERSION.zip nfprogress.app && cd ..