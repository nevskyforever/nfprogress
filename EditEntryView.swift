import SwiftUI
import SwiftData

struct EditEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var entry: Entry

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
    }
}
