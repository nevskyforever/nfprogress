import SwiftUI
import SwiftData

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject

    @State private var date = Date()
    @State private var characterCount = 0

    var body: some View {
        VStack(spacing: 16) {
            Text("Новая запись")
                .font(.title2.bold())

            DatePicker("Дата и время", selection: $date)
                .labelsHidden()

            TextField("Символов", value: $characterCount, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 120)

            Spacer()

            Button("Добавить") {
                let newEntry = Entry(date: date, characterCount: characterCount)
                project.entries.append(newEntry)
                dismiss()
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }
}
