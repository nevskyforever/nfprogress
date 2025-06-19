import SwiftUI

struct MainMenuCommands: Commands {
    var body: some Commands {
        CommandMenu("Файл") {
            Button("Новый проект") {
                NotificationCenter.default.post(name: .menuAddProject, object: nil)
            }
            .keyboardShortcut("n", modifiers: [.command, .shift])

            Divider()

            Button("Импортировать\u{2026}") {
                NotificationCenter.default.post(name: .menuImport, object: nil)
            }
            .keyboardShortcut("i", modifiers: .command)

            Button("Экспортировать\u{2026}") {
                NotificationCenter.default.post(name: .menuExport, object: nil)
            }
            .keyboardShortcut("e", modifiers: .command)
        }

        CommandMenu("Проект") {
            Button("Новая запись") {
                NotificationCenter.default.post(name: .menuAddEntry, object: nil)
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("Новый этап") {
                NotificationCenter.default.post(name: .menuAddStage, object: nil)
            }
            .keyboardShortcut("n", modifiers: [.command, .option])
        }

    }
}
