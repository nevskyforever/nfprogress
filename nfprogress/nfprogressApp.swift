import SwiftUI
import SwiftData

@MainActor
@main
struct nfprogressApp: App {
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
    }
}

