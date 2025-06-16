import SwiftUI
import SwiftData

struct AddStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject

    @State private var title = ""
    @State private var goal = 1000

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
                .submitLabel(.done)
                .onSubmit(addStage)

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
        let stage = WritingProject(title: name, goal: goal, isStage: true)
        stage.parent = project
        modelContext.insert(stage)
        dismiss()
    }
}
