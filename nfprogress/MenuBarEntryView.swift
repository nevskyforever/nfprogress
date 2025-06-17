import SwiftUI
import SwiftData

struct MenuBarEntryView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    // Explicitly compare the archived flag as negation sometimes
    // fails to refresh the query results correctly
    @Query(filter: #Predicate<WritingProject> { $0.isArchived == false })
    private var projects: [WritingProject]

    @State private var selectedIndex: Int = 0
    @State private var characterCount: Int = 0
    @State private var date: Date = .now
    @State private var didSave: Bool = false
    @State private var showingArchive = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if projects.isEmpty {
                Text("Нет проектов")
            } else {
                Picker("Проект", selection: $selectedIndex) {
                    ForEach(Array(projects.enumerated()), id: \.offset) { idx, project in
                        Text(project.title).tag(idx)
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
            Button("Архивированные") {
                showingArchive = true
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
        .sheet(isPresented: $showingArchive) {
            ArchivedProjectsView()
                .environment(\.modelContext, modelContext)
        }
    }

    private func maybeSave() -> Bool {
        guard !didSave, isValid else { return false }
        let index = min(max(selectedIndex, 0), projects.count - 1)
        let project = projects[index]
        let entry = Entry(date: date, characterCount: characterCount)
        project.entries.append(entry)
        try? modelContext.save()
        didSave = true
        resetFields()
        return true
    }

    private var isValid: Bool {
        !projects.isEmpty && characterCount > 0
    }

    private func resetFields() {
        characterCount = 0
        date = .now
    }
}
