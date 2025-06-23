#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif
#if os(macOS)
import AppKit
#endif

@MainActor
@main
struct nfprogressApp: App {
    init() {
#if os(macOS)
        let raw = UserDefaults.standard.string(forKey: "language") ?? AppLanguage.system.rawValue
        let lang = AppLanguage(rawValue: raw) ?? .system
        DispatchQueue.main.async {
            Self.localizeMenus(language: lang)
        }
#endif
    }
    /// Global application settings available across all scenes
    @StateObject var settings = AppSettings()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(settings)
                .environment(\.locale, settings.locale)
#if os(macOS)
                .windowTitle("NFProgress")
                .defaultSize(width: layoutStep(48), height: layoutStep(30))
#endif
        }
        .modelContainer(DataController.shared)
        .commands { MainMenuCommands() }
        #if os(macOS)
        .onChange(of: settings.language) { newLang in
            Self.localizeMenus(language: newLang)
        }
        #endif

        #if os(macOS)
        MenuBarExtra("NFProgress", systemImage: "text.cursor") {
            MenuBarEntryView()
                .environmentObject(settings)
                .environment(\.locale, settings.locale)
                .windowTitle("NFProgress")
        }
        .menuBarExtraStyle(.window)
        .modelContainer(DataController.shared)
        #endif

#if os(macOS)
        additionalWindows
#endif

#if os(macOS)
        Settings {
            SettingsView()
                .environmentObject(settings)
                .environment(\.locale, settings.locale)
        }
#endif
    }
}

#if os(macOS)
extension nfprogressApp {
    private static func localizeMenus(language: AppLanguage) {
        guard let mainMenu = NSApp.mainMenu else { return }

        for item in mainMenu.items {
            switch item.title {
            case "File", "Файл":
                item.title = (language == .ru) ? "Файл" : "File"
            case "Edit", "Правка":
                item.title = (language == .ru) ? "Правка" : "Edit"
            case "View", "Вид":
                item.title = (language == .ru) ? "Вид" : "View"
            case "Project", "Проект":
                item.title = (language == .ru) ? "Проект" : "Project"
            case "Window", "Окно":
                item.title = (language == .ru) ? "Окно" : "Window"
            case "Help", "Справка":
                item.title = (language == .ru) ? "Справка" : "Help"
            default:
                break
            }

            if let submenu = item.submenu {
                for subItem in submenu.items {
                    switch subItem.title {
                    // MARK: - Application menu
                    case "About nfprogress", "О приложении nfprogress":
                        subItem.title = language == .ru ? "О приложении nfprogress" : "About nfprogress"
                    case "Settings…", "Preferences…", "Настройки…":
                        subItem.title = language == .ru ? "Настройки…" : "Settings…"
                    case "Hide nfprogress", "Скрыть nfprogress":
                        subItem.title = language == .ru ? "Скрыть nfprogress" : "Hide nfprogress"
                    case "Hide Others", "Скрыть другие":
                        subItem.title = language == .ru ? "Скрыть другие" : "Hide Others"
                    case "Show All", "Показать все":
                        subItem.title = language == .ru ? "Показать все" : "Show All"
                    case "Quit nfprogress", "Завершить nfprogress":
                        subItem.title = language == .ru ? "Завершить nfprogress" : "Quit nfprogress"

                    // MARK: - File menu
                    case "New", "Новый":
                        subItem.title = language == .ru ? "Новый" : "New"
                    case "Open…", "Открыть…":
                        subItem.title = language == .ru ? "Открыть…" : "Open…"
                    case "Close", "Закрыть":
                        subItem.title = language == .ru ? "Закрыть" : "Close"
                    case "Save", "Сохранить":
                        subItem.title = language == .ru ? "Сохранить" : "Save"
                    case "Save As…", "Сохранить как…":
                        subItem.title = language == .ru ? "Сохранить как…" : "Save As…"
                    case "Revert", "Восстановить":
                        subItem.title = language == .ru ? "Восстановить" : "Revert"
                    case "Page Setup…", "Параметры страницы…":
                        subItem.title = language == .ru ? "Параметры страницы…" : "Page Setup…"
                    case "Print…", "Печать…":
                        subItem.title = language == .ru ? "Печать…" : "Print…"

                    // MARK: - Edit menu
                    case "Undo", "Отменить":
                        subItem.title = language == .ru ? "Отменить" : "Undo"
                    case "Redo", "Повторить":
                        subItem.title = language == .ru ? "Повторить" : "Redo"
                    case "Cut", "Вырезать":
                        subItem.title = language == .ru ? "Вырезать" : "Cut"
                    case "Copy", "Копировать":
                        subItem.title = language == .ru ? "Копировать" : "Copy"
                    case "Paste", "Вставить":
                        subItem.title = language == .ru ? "Вставить" : "Paste"
                    case "Delete", "Удалить":
                        subItem.title = language == .ru ? "Удалить" : "Delete"
                    case "Select All", "Выбрать все":
                        subItem.title = language == .ru ? "Выбрать все" : "Select All"

                    // MARK: - View menu
                    case "Enter Full Screen", "Во весь экран":
                        subItem.title = language == .ru ? "Во весь экран" : "Enter Full Screen"
                    case "Exit Full Screen", "Выйти из полноэкранного режима":
                        subItem.title = language == .ru ? "Выйти из полноэкранного режима" : "Exit Full Screen"
                    case "Show Toolbar", "Показать панель инструментов":
                        subItem.title = language == .ru ? "Показать панель инструментов" : "Show Toolbar"
                    case "Hide Toolbar", "Скрыть панель инструментов":
                        subItem.title = language == .ru ? "Скрыть панель инструментов" : "Hide Toolbar"
                    case "Customize Toolbar…", "Настроить панель инструментов…":
                        subItem.title = language == .ru ? "Настроить панель инструментов…" : "Customize Toolbar…"

                    // MARK: - Window menu
                    case "Minimize", "Свернуть":
                        subItem.title = language == .ru ? "Свернуть" : "Minimize"
                    case "Zoom", "Увеличить":
                        subItem.title = language == .ru ? "Увеличить" : "Zoom"
                    case "Close Window", "Закрыть окно":
                        subItem.title = language == .ru ? "Закрыть окно" : "Close Window"
                    case "Tile Window to Left of Screen", "Разместить окно слева":
                        subItem.title = language == .ru ? "Разместить окно слева" : "Tile Window to Left of Screen"
                    case "Tile Window to Right of Screen", "Разместить окно справа":
                        subItem.title = language == .ru ? "Разместить окно справа" : "Tile Window to Right of Screen"
                    case "Bring All to Front", "Разместить все поверх":
                        subItem.title = language == .ru ? "Разместить все поверх" : "Bring All to Front"

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
