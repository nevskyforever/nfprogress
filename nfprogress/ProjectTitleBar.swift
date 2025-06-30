#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

/// Отображает название проекта в панели инструментов
/// и позволяет редактировать его при нажатии.
struct ProjectTitleBar: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject
    @State private var isEditing = false
    @FocusState private var isFocused: Bool

    var body: some View {
        Group {
            if isEditing {
                TextField("", text: $project.title, onEditingChanged: { editing in
                        if !editing { save() }
                    }, onCommit: save)
                    .textFieldStyle(.roundedBorder)
                    .focused($isFocused)
                    .onAppear { isFocused = true }
#if os(macOS)
                    .onExitCommand { save() }
#endif
                    .frame(maxWidth: 200)
            } else {
                Text(project.title)
                    .font(.headline)
                    .onTapGesture {
                        isEditing = true
                        isFocused = true
                    }
            }
        }
        .onDisappear {
            if isEditing { save() }
        }
    }

    private func save() {
        isEditing = false
        do {
            try modelContext.save()
            #if canImport(SwiftData)
            ProgressAnimationTracker.setProgress(project.progress, for: project)
            #endif
        } catch {
            print("Ошибка сохранения: \(error)")
        }
    }
}

/// Обёртка для необязательного проекта.
struct OptionalProjectTitleBar: View {
    var project: WritingProject?

    var body: some View {
        if let project {
            ProjectTitleBar(project: project)
        } else {
            Text("nfprogress")
                .font(.headline)
        }
    }
}
#endif
