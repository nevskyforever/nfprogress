#if canImport(SwiftUI)
import SwiftUI

struct MainMenuCommands: Commands {
    var body: some Commands {
        // Дополнительные команды в стандартном меню File
        CommandGroup(after: .newItem) {
            Button("new_project") {
                NotificationCenter.default.post(name: .menuAddProject, object: nil)
            }
            .keyboardShortcut("n", modifiers: [.command, .shift])

            Divider()

            Button("import_ellipsis") {
                NotificationCenter.default.post(name: .menuImport, object: nil)
            }
            .keyboardShortcut("i", modifiers: .command)

            Button("export_ellipsis") {
                NotificationCenter.default.post(name: .menuExport, object: nil)
            }
            .keyboardShortcut("e", modifiers: .command)
        }

        CommandMenu("menu_project") {
            Button("new_entry") {
                NotificationCenter.default.post(name: .menuAddEntry, object: nil)
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("new_stage") {
                NotificationCenter.default.post(name: .menuAddStage, object: nil)
            }
            .keyboardShortcut("n", modifiers: [.command, .option])
        }

    }
}
#endif
