import SwiftUI
import SwiftData

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    /// Stage that the entry should be added to if provided.
    /// When set, the stage picker is hidden and the entry is
    /// automatically assigned to this stage.
    private let fixedStage: Stage?
    @State private var selectedStageIndex: Int

    @State private var date = Date()
    @State private var characterCount = 0

    init(project: WritingProject, stage: Stage? = nil) {
        self.project = project
        self.fixedStage = stage
        if let stage,
           let found = project.stages.firstIndex(where: { $0.id == stage.id }) {
            _selectedStageIndex = State(initialValue: found)
        } else {
            _selectedStageIndex = State(initialValue: 0)
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

            Text("Новая запись")
                .font(.title2.bold())

            DatePicker("Дата и время", selection: $date)
                .labelsHidden()

            if fixedStage == nil && !project.stages.isEmpty {
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
                .submitLabel(.done)
                .onSubmit(addEntry)

            Spacer()

            Button("Добавить") {
                addEntry()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
        .onDisappear {
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }

    private func addEntry() {
        let newEntry: Entry
        if project.stages.isEmpty {
            // Entry belongs directly to the project
            let delta = characterCount - project.currentProgress
            newEntry = Entry(date: date, characterCount: delta)
            project.entries.append(newEntry)
        } else {
            let stage: Stage
            if let fixedStage {
                stage = fixedStage
            } else {
                let index = min(max(selectedStageIndex, 0), project.stages.count - 1)
                stage = project.stages[index]
            }

            // Convert the entered stage progress into a delta relative to the stage
            // itself so that other stages are unaffected.
            let delta = characterCount - stage.currentProgress
            newEntry = Entry(date: date, characterCount: delta)
            stage.entries.append(newEntry)
        }

        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}
