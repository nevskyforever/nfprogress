import SwiftUI

struct MainMenuCommands: Commands {
    var body: some Commands {
        CommandMenu("Файл") {}
        CommandMenu("Проект") {}
        CommandMenu("Добавить запись") {}
        CommandGroup(replacing: .appSettings) {
            Button("Настройки") {}
        }
    }
}
