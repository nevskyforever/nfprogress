import SwiftUI
import SwiftData

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject

    @State private var date = Date()
    @State private var characterCount = 0
    @State private var selectedStage = 0

    var body: some View {
        VStack(spacing: 16) {
            Text("Новая запись")
                .font(.title2.bold())

            DatePicker("Дата и время", selection: $date)
                .labelsHidden()

            if !project.stages.isEmpty {
                Picker("Этап", selection: $selectedStage) {
                    Text("Без этапа").tag(0)
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title).tag(idx + 1)
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
    }

    private func addEntry() {
        let stage = selectedStage > 0 ? project.stages[selectedStage - 1] : nil
        let newEntry = Entry(date: date, characterCount: characterCount, stage: stage)
        if let stage {
            stage.entries.append(newEntry)
        } else {
            project.entries.append(newEntry)
        }
        dismiss()
    }
}
