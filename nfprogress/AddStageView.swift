import SwiftUI
import SwiftData

struct AddStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject

    @State private var title = ""
    @State private var goal = 1000

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

            Text("Новый этап")
                .font(.title2.bold())
            TextField("Название", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            TextField("Цель", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            Spacer()
            Button("Создать") { addStage() }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func addStage() {
        let name = title.isEmpty ? "Этап" : title
        let stage = Stage(title: name, goal: goal, startProgress: project.currentProgress)
        project.stages.append(stage)
        dismiss()
    }
}

