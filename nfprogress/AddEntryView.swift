import SwiftUI
import SwiftData

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    var stage: Stage?

    @State private var date = Date()
    @State private var characterCount = 0

    var body: some View {
        VStack(spacing: 16) {
            Text("Новая запись" + (stage != nil ? " в \(stage!.title)" : ""))
                .font(.title2.bold())

            DatePicker("Дата и время", selection: $date)
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
    }

    private func addEntry() {
        let newEntry = Entry(date: date, characterCount: characterCount)
        if let stage {
            stage.entries.append(newEntry)
        } else {
            project.entries.append(newEntry)
        }
        dismiss()
    }
}
