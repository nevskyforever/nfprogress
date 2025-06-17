import SwiftUI
import SwiftData

struct AddStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject

    @State private var title = ""
    @State private var goal = 1000
    @State private var deadline: Date = .now
    @State private var hasDeadline = false

    var body: some View {
        VStack(spacing: 16) {
            Text("Новый этап")
                .font(.title2.bold())

            TextField("Название", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            TextField("Цель", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            Toggle("Дедлайн", isOn: $hasDeadline)
            if hasDeadline {
                DatePicker("", selection: $deadline, displayedComponents: .date)
                    .labelsHidden()
            }

            Spacer()

            Button("Создать") {
                addStage()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func addStage() {
        let name = title.isEmpty ? "Новый этап" : title
        let newStage = Stage(title: name, goal: goal, deadline: hasDeadline ? deadline : nil)
        project.stages.append(newStage)
        dismiss()
    }
}
