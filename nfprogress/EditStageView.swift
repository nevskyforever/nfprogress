import SwiftUI
import SwiftData

struct EditStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var stage: Stage

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

            Text("Редактировать этап")
                .font(.title2.bold())

            TextField("Название", text: $stage.title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            TextField("Цель", value: $stage.goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

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
        .onChange(of: stage.goal) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }
}
