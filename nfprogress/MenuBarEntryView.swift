import SwiftUI
import SwiftData

struct MenuBarEntryView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    @Query private var projects: [WritingProject]

    @State private var selectedIndex: Int = 0
    @State private var selectedStageIndex: Int = 0
    @State private var characterCount: Int = 0
    @State private var date: Date = .now
    @State private var didSave: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
            }

            if projects.isEmpty {
                Text("Нет проектов")
            } else {
                Picker("Проект", selection: $selectedIndex) {
                    ForEach(Array(projects.enumerated()), id: \.offset) { idx, project in
                        Text(project.title).tag(idx)
                    }
                }
                .labelsHidden()
                let project = projects[min(max(selectedIndex, 0), projects.count - 1)]
                if !project.stages.isEmpty {
                    Picker("Этап", selection: $selectedStageIndex) {
                        Text("Без этапа").tag(0)
                        ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                            Text(stage.title).tag(idx + 1)
                        }
                    }
                    .labelsHidden()
                }
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
        .onChange(of: selectedIndex) { _ in
            selectedStageIndex = 0
        }
    }

    private func maybeSave() -> Bool {
        guard !didSave, isValid else { return false }
        let index = min(max(selectedIndex, 0), projects.count - 1)
        let project = projects[index]
        let absoluteCount = project.currentProgress + characterCount
        let entry = Entry(date: date, characterCount: absoluteCount)
        if selectedStageIndex > 0 && selectedStageIndex - 1 < project.stages.count {
            let stage = project.stages[selectedStageIndex - 1]
            stage.entries.append(entry)
        } else {
            project.entries.append(entry)
        }
        try? modelContext.save()
        didSave = true
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        resetFields()
        return true
    }

    private var isValid: Bool {
        !projects.isEmpty && characterCount > 0
    }

    private func resetFields() {
        characterCount = 0
        date = .now
        selectedStageIndex = 0
    }
}
