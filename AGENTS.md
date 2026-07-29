## About the project

This is a Python desktop application with a PySide6 GUI for writers to track their writing progress, with optional gamification features.

The application is built with Nuitka for:

* Windows;
* macOS Apple Silicon;
* macOS Intel.

## General working rules

* Perform only the task specified by the user.
* Do not modify unrelated parts of the project.
* Do not perform a full refactor without an explicit request.
* Before changing code, find related files and usage sites.
* Use `rg` to search the project.
* Do not inspect the entire project if the task concerns a single module.
* Preserve the existing architecture and style.
* Do not add dependencies unless necessary.
* Do not change public application behavior without an explicit request.

## Working with files

* First identify the smallest set of files needed for the task.
* Do not open large files in full when locating the relevant function or class is sufficient.
* Do not modify build files, dependencies, or configuration unless necessary.
* Do not modify generated files.
* Do not delete code until you have verified that it is unused.

## Python

* Use features available in the project's current Python version.
* Add type annotations where they improve clarity.
* Do not suppress exceptions with an empty `except`.
* Do not use global variables unless necessary.
* Keep function, class, and variable names clear.
* Do not complicate the solution with unnecessary abstractions.

## PySide6

* Do not run long operations in the GUI main thread.
* Do not block the UI with network requests, waiting, or expensive computations.
* Follow the existing signal and slot system.
* Do not change the UI structure without an explicit request.
* Account for Windows and macOS compatibility.

## Localization

Russian is the source language for the interface and keys. Supported languages are Russian, English, Spanish, German, French, and Brazilian Portuguese.

When adding or changing user-facing text, always account for localization:

* Translate text from Python code through `localization.tr()`.
* Use `localization.LocalizedMessageBox` for `QMessageBox`; it translates both the title and message automatically.
* `NotificationManager.show_success()`, `show_error()`, `show_warning()`, and `show_info()` also call `tr()` automatically. Pass them the source Russian string that exists in the catalog.
* Add new permanent labels, buttons, and other UI elements to the appropriate `UI template/*.ui` file. Do not add them manually to generated `UI_fiiles/*.py` files.
* When switching language, open forms must call their `retranslateUi()`, and lists and labels populated from Python must be filled again.
* Do not translate user data: project names, stages, custom awards, files, or text entered by the user.

Examples:

```python
label.setText(tr("Настройки"))
label.setText(tr(f"⭐ Уровень: {level}"))
notifications.show_success("Изменения сохранены")
QMessageBox.warning(parent, "Ошибка", "Сначала выберите проект")
```

Translate a dynamic string by components when it embeds another translatable object. Translating an entire template preserves a dynamic value as-is, so the following code can leave a Russian item name inside translated text:

```python
# Incorrect for an embedded item: item.name remains Russian.
tr(f"Куплено: {item.name}")

# Correct:
f"{tr('Куплено')}: {localized_game_name(item.name)}"
```

For game-related code, follow these rules:

* Do not translate or change internal item names, buffs, categories, statuses, or dictionary keys in `game_data.py`, save files, or `Qt.UserRole`. Game logic continues to use canonical Russian values.
* Use `game_UI.localized_game_name()` for displayed names of built-in items and buffs. It handles an emoji prepended to the name separately.
* Use `game_UI.localized_game_description()` for dynamic buff descriptions.
* Use `game_UI.localized_item_result()` for an item-use result.
* Translate a displayed category separately with `tr(category)`, but retain the source category in list item data.

For example:

```python
display_text = (
    f"{localized_game_name(item.name)} x{count} [{tr(category)}]"
)
list_item.setText(display_text)
list_item.setData(Qt.ItemDataRole.UserRole, (category, item_key))
```

`translations_catalog.py` is generated automatically and must not be edited manually. If new Russian strings are added:

1. Ensure the strings are in `UI template/*.ui` or in a Python file listed in `PYTHON_SOURCES` in `scripts/generate_translations.py`.
2. If you add a Python module containing user-facing strings, add only that module to `PYTHON_SOURCES`.
3. Run `python3 scripts/generate_translations.py`. The script needs internet access and regenerates the entire catalog, so review the diff carefully and do not accept unrelated translation regressions.
4. Add manual terminology fixes and short translations that the generator cannot reliably derive from a dynamic string to `TRANSLATION_OVERRIDES` in `localization.py` for all five non-Russian languages.

After localization changes, run at least:

```bash
python3 -m py_compile localization.py <changed Python files>
python3 -m pytest -q tests/test_localization.py
```

Verify that new text is translated into all five languages, dynamic values are preserved, and internal game-object keys remain unchanged. The user agreement is intentionally displayed in a single English version for every non-Russian language.

## Building

* Do not run a full Nuitka build unless necessary.
* Do not run builds for all platforms simultaneously unless the task requires it.
* When changing build scripts, check the differences between Windows, macOS ARM, and macOS Intel.
* Do not change publication paths, SSH settings, keys, or server data without an explicit request.
* Do not expose secrets, tokens, passwords, or private keys.

## Verifying changes

After making changes:

1. Check syntax of affected Python files.
2. Run only tests relevant to the task.
3. Check imports of modified modules.
4. Test the modified function in isolation when possible.
5. Do not run the full test suite when a focused check is sufficient.

If no tests cover the modified code, report that fact.

## Response format

After completing a task, provide a brief report:

* what was changed;
* which files were affected;
* which checks were performed;
* whether known limitations or risks remain.

Do not describe obvious commands or search steps in detail.
