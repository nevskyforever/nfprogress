#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct AddProjectView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var settings: AppSettings
    @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]

    @State private var title = ""
    @State private var goal = 10000

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(25)
    private let minWidth: CGFloat = layoutStep(35)
    private let minHeight: CGFloat = layoutStep(20)

    var body: some View {
        VStack(spacing: viewSpacing) {
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
        .scaledPadding(1, [.horizontal, .bottom])
        .scaledPadding(2, .top)
        .frame(minWidth: minWidth, minHeight: minHeight)
#if os(macOS)
        .onExitCommand { dismiss() }
#endif
    }

    private func addProject() {
        let name = title.isEmpty ? settings.localized("new_text") : title
        let maxOrder = projects.map(\.order).max() ?? -1
        let newProject = WritingProject(title: name, goal: goal, order: maxOrder + 1)
        modelContext.insert(newProject)
#if canImport(SwiftData)
        ProgressAnimationTracker.addProject(newProject)
#endif
        dismiss()
    }
}

#endif
