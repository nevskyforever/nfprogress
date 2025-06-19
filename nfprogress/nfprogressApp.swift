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
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(DataController.shared)
        .commands { MainMenuCommands() }

        MenuBarExtra("NFProgress", systemImage: "text.cursor") {
            MenuBarEntryView()
        }
        .menuBarExtraStyle(.window)
        .modelContainer(DataController.shared)

#if os(macOS)
        Settings {
            SettingsView()
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

            if let submenu = item.submenu,
               item.title.contains("nfprogress") || item.title.contains("NFProgress") {
                for subItem in submenu.items {
                    switch subItem.title {
                    case "About nfprogress":
                        subItem.title = "О приложении nfprogress"
                    case "Settings…":
                        subItem.title = "Настройки…"
                    case "Hide nfprogress":
                        subItem.title = "Скрыть nfprogress"
                    case "Hide Others":
                        subItem.title = "Скрыть другие"
                    case "Show All":
                        subItem.title = "Показать все"
                    case "Quit nfprogress":
                        subItem.title = "Завершить nfprogress"
                    default:
                        break
                    }
                }
            }
        }
    }
}
#endif

