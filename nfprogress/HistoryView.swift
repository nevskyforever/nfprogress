#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct HistoryView: View {
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject
    @Binding var editingEntry: Entry?

    private func stageForEntry(_ entry: Entry) -> Stage? {
        for stage in project.stages {
            if stage.entries.contains(where: { $0.id == entry.id }) {
                return stage
            }
        }
        return nil
    }

    var body: some View {
        ForEach(project.sortedEntries) { entry in
            let total = project.globalProgress(for: entry)
            let prevTotal = project.previousGlobalProgress(before: entry)
            let delta = total - prevTotal
            let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
            let progressPercent = Double(total) / Double(max(project.goal, 1)) * 100
            let stageName = stageForEntry(entry)?.title

            HStack {
                VStack(alignment: .leading) {
                    if let stageName {
                        Text(settings.localized("stage_colon", stageName))
                    }
                    Text(settings.localized("characters_count", total))
                    Text(settings.localized("change_format", delta, deltaPercent))
                        .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                    Text(settings.localized("progress_format", progressPercent))
                        .font(.caption)
                        .foregroundColor(.gray)
                    Text(entry.date.formatted(date: .numeric, time: .shortened))
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                Spacer()
                Button { editingEntry = entry } label: {
                    Image(systemName: "pencil")
                }
                Button(role: .destructive) {
                    if let stage = stageForEntry(entry) {
                        if let i = stage.entries.firstIndex(where: { $0.id == entry.id }) {
                            stage.entries.remove(at: i)
                        }
                    } else if let i = project.entries.firstIndex(where: { $0.id == entry.id }) {
                        project.entries.remove(at: i)
                    }
                    modelContext.delete(entry)
                    try? modelContext.save()
                    NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
                } label: {
                    Image(systemName: "trash")
                }
            }
        }
    }
}
#endif
