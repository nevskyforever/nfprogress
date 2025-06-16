import SwiftUI
import SwiftData

@main
struct nfprogressApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [WritingProject.self, Entry.self])
    }
}

