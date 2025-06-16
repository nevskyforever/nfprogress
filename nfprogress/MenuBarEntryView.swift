import SwiftUI
import SwiftData

struct MenuBarEntryView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    @Query(
        filter: #Predicate<WritingProject> { !$0.isStage },
        sort: [SortDescriptor(\.title)]
    )
    private var projects: [WritingProject]

    @State private var selectedIndex: Int = 0
    @State private var characterCount: Int = 0
    @State private var date: Date = .now
    @State private var didSave: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            let items: [(WritingProject, String)] = allItems.map { project in
                if project.isStage,
                   let parent = projects.first(where: { $0.stages.contains(where: { $0.id == project.id }) }) {
                    return (project, "\(parent.title) – \(project.title)")
                } else {
                    return (project, project.title)
                }
            }
            if items.isEmpty {
                Text("Нет проектов")
            } else {
                Picker("Проект", selection: $selectedIndex) {
                    ForEach(Array(items.enumerated()), id: \.offset) { idx, pair in
                        Text(pair.1).tag(idx)
                    }
                }
                .labelsHidden()
                TextField("Символов", value: $characterCount, format: .number)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 160)
                    .onSubmit {
                        if maybeSave() { dismiss() }
                    }
                DatePicker("Дата", selection: $date)
                    .labelsHidden()
                Button("Добавить") {
                    if maybeSave() { dismiss() }
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding()
        .frame(width: 200)
        .onDisappear {
            _ = maybeSave()
        }
        .onAppear {
            didSave = false
        }
    }

    private func maybeSave() -> Bool {
        guard !didSave, isValid else { return false }
        let items = allItems
        let index = min(max(selectedIndex, 0), items.count - 1)
        let project = items[index]
        let entry = Entry(date: date, characterCount: characterCount)
        project.entries.append(entry)
        try? modelContext.save()
        didSave = true
        resetFields()
        return true
    }

    private var isValid: Bool {
        !allItems.isEmpty && characterCount > 0
    }

    private var allItems: [WritingProject] {
        var result: [WritingProject] = []
        for project in projects {
            result.append(project)
            result.append(contentsOf: project.stages)
        }
        return result
    }

    private func resetFields() {
        characterCount = 0
        date = .now
    }
}
