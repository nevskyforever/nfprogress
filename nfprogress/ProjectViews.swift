#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct AddProjectView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]

    @State private var title = ""
    @State private var goal = 10000

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(25)
    private let minWidth: CGFloat = layoutStep(30)

    var body: some View {
        VStack(spacing: viewSpacing) {

            Text("new_project")
                .font(.title2.bold())
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            TextField("project_name", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)

            TextField("project_goal", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)
                .submitLabel(.done)
                .onSubmit(addProject)

            Spacer()

            Button("create") {
                addProject()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .scaledPadding(1, .bottom)
        }
        .scaledPadding()
        .frame(minWidth: minWidth)
    }

    private func addProject() {
        let name = title.isEmpty ? String(localized: "new_text") : title
        let maxOrder = projects.map(\.order).max() ?? -1
        let newProject = WritingProject(title: name, goal: goal, order: maxOrder + 1)
        modelContext.insert(newProject)
        dismiss()
    }
}

#endif
