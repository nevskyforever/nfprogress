import SwiftUI
import SwiftData

struct HistoryView: View {
    @Environment(\.modelContext) private var modelContext
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
            let index = project.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
            let prevCount = index > 0 ? project.sortedEntries[index - 1].characterCount : 0
            let delta = entry.characterCount - prevCount
            let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
            let progressPercent = Double(entry.characterCount) / Double(max(project.goal, 1)) * 100
            let stageName = stageForEntry(entry)?.title

            HStack {
                VStack(alignment: .leading) {
                    if let stageName {
                        Text("Этап: \(stageName)")
                    }
                    Text("Символов: \(entry.characterCount)")
                    Text(String(format: "Вклад: %d (%.0f%%)", delta, deltaPercent))
                        .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                    Text(String(format: "Прогресс: %.0f%%", progressPercent))
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
                } label: {
                    Image(systemName: "trash")
                }
            }
        }
    }
}
