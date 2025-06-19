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

            Text("new_stage")
                .font(.title2.bold())
            if project.stages.isEmpty && !project.entries.isEmpty {
                Text("all_entries_move")
                    .multilineTextAlignment(.center)
                    .font(.caption)
                    .foregroundColor(.orange)
            }
            TextField("project_name", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            TextField("project_goal", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            Spacer()
            Button("create") { addStage() }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func addStage() {
        let name = title.isEmpty ? String(localized: "stage_placeholder") : title
        let start = (project.stages.isEmpty && !project.entries.isEmpty) ? 0 : project.currentProgress
        let stage = Stage(title: name, goal: goal, startProgress: start)
        if project.stages.isEmpty && !project.entries.isEmpty {
            stage.entries = project.entries
            project.entries.removeAll()
        }
        project.stages.append(stage)
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}

