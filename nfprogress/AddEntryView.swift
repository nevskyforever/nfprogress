import SwiftUI
import SwiftData

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    @State private var selectedStageIndex: Int

    @State private var date = Date()
    @State private var characterCount = 0

    init(project: WritingProject, stage: Stage? = nil) {
        self.project = project
        let idx: Int
        if let stage, let found = project.stages.firstIndex(where: { $0.id == stage.id }) {
            idx = found + 1
        } else {
            idx = 0
        }
        _selectedStageIndex = State(initialValue: idx)
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

            Picker("Этап", selection: $selectedStageIndex) {
                Text("Без этапа").tag(0)
                ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                    Text(stage.title).tag(idx + 1)
                }
            }
            .labelsHidden()

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
        let newEntry = Entry(date: date, characterCount: characterCount)
        if selectedStageIndex > 0 && selectedStageIndex - 1 < project.stages.count {
            let stage = project.stages[selectedStageIndex - 1]
            stage.entries.append(newEntry)
        } else {
            project.entries.append(newEntry)
        }
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}
