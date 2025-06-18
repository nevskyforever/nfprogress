import SwiftUI
import SwiftData

struct EditEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var entry: Entry
    @State private var date: Date
    @State private var characterCount: Int

    init(entry: Entry) {
        self.entry = entry
        _date = State(initialValue: entry.date)
        _characterCount = State(initialValue: entry.characterCount)
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
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}
