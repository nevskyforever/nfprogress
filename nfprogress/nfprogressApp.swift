#if canImport(SwiftUI)
import SwiftUI
import SwiftData
#if os(macOS)
import AppKit
#endif

@MainActor
@main
struct nfprogressApp: App {
    init() {
#if os(macOS)
        DispatchQueue.main.async {
            Self.localizeMenus()
        }
#endif
    }
    @StateObject private var settings = AppSettings()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.textScale, settings.textScale)
                .environmentObject(settings)
        }
        .modelContainer(DataController.shared)
        .commands { MainMenuCommands() }

        MenuBarExtra("NFProgress", systemImage: "text.cursor") {
            MenuBarEntryView()
                .environment(\.textScale, settings.textScale)
                .environmentObject(settings)
        }
        .menuBarExtraStyle(.window)
        .modelContainer(DataController.shared)

#if os(macOS)
        additionalWindows
#endif

#if os(macOS)
        Settings {
            SettingsView()
                .environment(\.textScale, settings.textScale)
                .environmentObject(settings)
        }
#endif
    }
}

#if os(macOS)
extension nfprogressApp {
    private static func localizeMenus() {
        guard let mainMenu = NSApp.mainMenu else { return }

        for item in mainMenu.items {
            switch item.title {
            case "File":
                item.title = "Файл"
            case "Edit":
                item.title = "Правка"
            case "View":
                item.title = "Вид"
            case "Project":
                item.title = "Проект"
            case "Window":
                item.title = "Окно"
            case "Help":
                item.title = "Справка"
            default:
                break
            }

            if let submenu = item.submenu {
                for subItem in submenu.items {
                    switch subItem.title {
                    // MARK: - Меню приложения
                    case "About nfprogress":
                        subItem.title = "О приложении nfprogress"
                    case "Settings…", "Preferences…":
                        subItem.title = "Настройки…"
                    case "Hide nfprogress":
                        subItem.title = "Скрыть nfprogress"
                    case "Hide Others":
                        subItem.title = "Скрыть другие"
                    case "Show All":
                        subItem.title = "Показать все"
                    case "Quit nfprogress":
                        subItem.title = "Завершить nfprogress"

                    // MARK: - Меню File
                    case "New":
                        subItem.title = "Новый"
                    case "Open…":
                        subItem.title = "Открыть…"
                    case "Close":
                        subItem.title = "Закрыть"
                    case "Save":
                        subItem.title = "Сохранить"
                    case "Save As…":
                        subItem.title = "Сохранить как…"
                    case "Revert":
                        subItem.title = "Восстановить"
                    case "Page Setup…":
                        subItem.title = "Параметры страницы…"
                    case "Print…":
                        subItem.title = "Печать…"

                    // MARK: - Меню Edit
                    case "Undo":
                        subItem.title = "Отменить"
                    case "Redo":
                        subItem.title = "Повторить"
                    case "Cut":
                        subItem.title = "Вырезать"
                    case "Copy":
                        subItem.title = "Копировать"
                    case "Paste":
                        subItem.title = "Вставить"
                    case "Delete":
                        subItem.title = "Удалить"
                    case "Select All":
                        subItem.title = "Выбрать все"

                    // MARK: - Меню View
                    case "Enter Full Screen":
                        subItem.title = "Во весь экран"
                    case "Exit Full Screen":
                        subItem.title = "Выйти из полноэкранного режима"
                    case "Show Toolbar":
                        subItem.title = "Показать панель инструментов"
                    case "Hide Toolbar":
                        subItem.title = "Скрыть панель инструментов"
                    case "Customize Toolbar…":
                        subItem.title = "Настроить панель инструментов…"

                    // MARK: - Меню Window
                    case "Minimize":
                        subItem.title = "Свернуть"
                    case "Zoom":
                        subItem.title = "Увеличить"
                    case "Close Window":
                        subItem.title = "Закрыть окно"
                    case "Tile Window to Left of Screen":
                        subItem.title = "Разместить окно слева"
                    case "Tile Window to Right of Screen":
                        subItem.title = "Разместить окно справа"
                    case "Bring All to Front":
                        subItem.title = "Разместить все поверх"

                    default:
                        break
                    }
                }
            }
        }
    }
}
#endif

#endif
