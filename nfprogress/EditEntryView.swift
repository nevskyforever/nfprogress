import SwiftUI
import SwiftData

struct EditEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    @Bindable var entry: Entry
    @State private var selectedStageIndex: Int = 0

    init(project: WritingProject, entry: Entry) {
        self.project = project
        self.entry = entry
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

            DatePicker("Дата и время", selection: $entry.date)
                .labelsHidden()

            if !project.stages.isEmpty {
                Picker("Этап", selection: $selectedStageIndex) {
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title).tag(idx)
                    }
                }
                .labelsHidden()
            }

            TextField("Символов", value: $entry.characterCount, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 120)

            Spacer()

            Button("Готово") {
                dismiss()
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
        .onDisappear {
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
        .onChange(of: entry.characterCount) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
        .onChange(of: entry.date) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
        .onChange(of: selectedStageIndex) { newValue in
            guard !project.stages.isEmpty else { return }
            moveEntry(to: project.stages[newValue])
        }
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
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
    }
}
