#if os(macOS)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct ExportProjectsView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @EnvironmentObject private var settings: AppSettings
    @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]

    @State private var selection = Set<PersistentIdentifier>()

    private var selectedProjects: [WritingProject] {
        projects.filter { selection.contains($0.id) }
    }

    var body: some View {
        VStack {
            List(selection: $selection) {
                ForEach(projects) { project in
                    Text(project.title)
                        .tag(project.id)
                }
            }
            .frame(minHeight: layoutStep(20))

            HStack {
                Spacer()
                Button(settings.localized("export")) { export() }
                    .buttonStyle(.borderedProminent)
                    .disabled(selection.isEmpty)
            }
        }
        .scaledPadding()
        .frame(minWidth: layoutStep(40), minHeight: layoutStep(30))
        .windowTitle(settings.localized("export_ellipsis"))
        .onExitCommand { dismiss() }
    }

    private func export() {
        let items = selectedProjects
        guard !items.isEmpty else { return }
        if items.count == 1, let project = items.first {
            exportSingle(project: project)
        } else {
            exportMultiple(projects: items)
        }
        dismiss()
    }

    private func exportSingle(project: WritingProject) {
        let csv = CSVManager.csvString(for: project)
        let name = project.title.replacingOccurrences(of: " ", with: "_") + ".csv"
        saveCSV(csv, defaultName: name)
    }

    private func exportMultiple(projects: [WritingProject]) {
        let csv = CSVManager.csvString(for: projects)
        saveCSV(csv, defaultName: "Projects.csv")
    }

    private func saveCSV(_ csv: String, defaultName: String) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.nameFieldStringValue = defaultName
        if panel.runModal() == .OK, let url = panel.url {
            do {
                try csv.write(to: url, atomically: true, encoding: .utf8)
            } catch {
                print("Export failed: \(error.localizedDescription)")
            }
        }
    }
}
#endif
