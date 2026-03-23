#!/bin/bash
VERSION=$(python3 -c "import engine; print(engine.version)")
echo "Сборка ARM, версия: $VERSION"

nuitka --standalone \
       --macos-create-app-bundle \
       --macos-app-icon=appIcon.icns \
       --macos-app-name="nfprogress" \
       --macos-app-version="$VERSION" \
       --company-name="nfproject" \
       --file-description="Трекер для писателей" \
       --enable-plugin=pyside6 \
       --output-dir=build-arm \
       --include-data-dir=/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/PySide6/Qt/translations=PySide6/Qt/translations \
       --lto=yes \
       --disable-ccache \
       --remove-output \
       --prefer-source-code \
       --follow-import-to=engine,game_UI,UI_fiiles \
       --python-flag=-O \
       main_UI.py && \
cd build-arm && mv main_UI.app nfprogress.app && zip -r nfprogress-mac-arm-$VERSION.zip nfprogress.app && cd ..