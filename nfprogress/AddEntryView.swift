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
        if let stage, let found = project.stages.firstIndex(where: { $0.id == stage.id }) {
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
        if project.stages.isEmpty {
            project.entries.append(newEntry)
        } else {
            let index = min(max(selectedStageIndex, 0), project.stages.count - 1)
            project.stages[index].entries.append(newEntry)
        }
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}
