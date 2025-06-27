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
                TextField("", text: $project.title)
                    .textFieldStyle(.roundedBorder)
                    .focused($isFocused)
                    .onSubmit(save)
                    .onAppear { isFocused = true }
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
    }

    private func save() {
        isEditing = false
        do { try modelContext.save() } catch {
            print("Ошибка сохранения: \(error)")
        }
    }
}

/// Обёртка для необязательного проекта.
struct OptionalProjectTitleBar: View {
    var project: WritingProject?

    var body: some View {
        HStack {
            Spacer(minLength: 0)
            if let project {
                ProjectTitleBar(project: project)
            } else {
                Text("nfprogress")
                    .font(.headline)
            }
        }
    }
}
#endif
