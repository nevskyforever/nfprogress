import SwiftUI
import SwiftData

struct AddProjectView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]

    @State private var title = ""
    @State private var goal = 10000

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

            Text("new_project")
                .font(.title2.bold())
                .applyTextScale()
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            TextField("project_name", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(minWidth: 200)

            TextField("project_goal", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(minWidth: 200)
                .submitLabel(.done)
                .onSubmit(addProject)

            Spacer()

            Button("create") {
                addProject()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .padding(.bottom)
        }
        .padding()
        .frame(minWidth: 320)
    }

    private func addProject() {
        let name = title.isEmpty ? String(localized: "new_text") : title
        let maxOrder = projects.map(\.order).max() ?? -1
        let newProject = WritingProject(title: name, goal: goal, order: maxOrder + 1)
        modelContext.insert(newProject)
        dismiss()
    }
}

