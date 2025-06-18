import SwiftUI
import SwiftData

struct EditStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var stage: Stage
    @State private var title: String
    @State private var goal: Int

    init(stage: Stage) {
        self.stage = stage
        _title = State(initialValue: stage.title)
        _goal = State(initialValue: stage.goal)
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

            Text("Редактировать этап")
                .font(.title2.bold())

            TextField("Название", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            TextField("Цель", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

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
        stage.title = title
        stage.goal = goal
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}
