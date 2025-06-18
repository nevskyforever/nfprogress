import SwiftUI
import SwiftData

struct EditEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    @Bindable var entry: Entry
    @State private var selectedStageIndex: Int = 0
    @State private var date: Date
    @State private var characterCount: Int

    init(project: WritingProject, entry: Entry) {
        self.project = project
        self.entry = entry
        _date = State(initialValue: entry.date)
        _characterCount = State(initialValue: entry.characterCount)
        if let stage = project.stageForEntry(entry),
           let idx = project.stages.firstIndex(where: { $0.id == stage.id }) {
            _selectedStageIndex = State(initialValue: idx)
        }
    }

    var body: some View {
        VStack(spacing: 16) {
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
            }

            Text("Редактировать запись")
                .font(.title2.bold())

            DatePicker("Дата и время", selection: $date)
                .labelsHidden()

            if !project.stages.isEmpty {
                Picker("Этап", selection: $selectedStageIndex) {
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title).tag(idx)
                    }
                }
                .labelsHidden()
            }

            TextField("Символов", value: $characterCount, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 120)

            Spacer()

            Button("Готово") {
                saveAndDismiss()
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func saveAndDismiss() {
        entry.date = date
        entry.characterCount = characterCount
        if !project.stages.isEmpty {
            let index = min(max(selectedStageIndex, 0), project.stages.count - 1)
            moveEntry(to: project.stages[index])
        }
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }

    private func moveEntry(to stage: Stage) {
        if let currentStage = project.stageForEntry(entry) {
            if let i = currentStage.entries.firstIndex(where: { $0.id == entry.id }) {
                currentStage.entries.remove(at: i)
            }
        } else if let idx = project.entries.firstIndex(where: { $0.id == entry.id }) {
            project.entries.remove(at: idx)
        }
        stage.entries.append(entry)
    }
}
