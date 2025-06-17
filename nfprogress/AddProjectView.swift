import SwiftUI
import SwiftData

struct AddProjectView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var title = ""
    @State private var goal = 10000

    var body: some View {
        VStack(spacing: 16) {
            Text("Новый проект")
                .font(.title2.bold())

            TextField("Название", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            TextField("Цель", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
                .submitLabel(.done)
                .onSubmit(addProject)

            Spacer()

            Button("Создать") {
                addProject()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func addProject() {
        let name = title.isEmpty ? "Новый текст" : title
        let newProject = WritingProject(title: name, goal: goal)
        modelContext.insert(newProject)
        try? modelContext.save()
        dismiss()
    }
}
