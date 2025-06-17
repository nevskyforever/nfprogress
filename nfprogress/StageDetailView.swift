import SwiftUI
import SwiftData

struct StageDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var stage: Stage

    @State private var showingAddEntry = false
    @State private var editingEntry: Entry?

    private let deadlineFormatter: DateFormatter = {
        let df = DateFormatter()
        df.locale = Locale(identifier: "ru_RU")
        df.dateFormat = "d MMMM yyyy"
        return df
    }()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(stage.title)
                    .font(.title)
                Text("Цель: \(stage.goal)")
                Text("Прогресс: \(stage.currentProgress)/\(stage.goal) (\(Int(stage.progressPercentage * 100))%)")
                if let deadline = stage.deadline {
                    Text("Дедлайн: \(deadlineFormatter.string(from: deadline))")
                    Text("Осталось дней: \(stage.daysLeft)")
                    if let target = stage.dailyTarget {
                        Text("Ежедневная цель: \(target) символов")
                    }
                }
                Text("Стик: \(stage.streak) дней подряд")

                Button("Добавить запись") {
                    showingAddEntry = true
                }

                ForEach(stage.sortedEntries) { entry in
                    let index = stage.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
                    let prevCount = index > 0 ? stage.sortedEntries[index - 1].characterCount : 0
                    let delta = entry.characterCount - prevCount
                    let deltaPercent = Double(delta) / Double(max(stage.goal, 1)) * 100
                    let deltaText = String(format: "%+d (%+.0f%%)", delta, deltaPercent)
                    let progressPercent = Double(entry.characterCount) / Double(max(stage.goal, 1)) * 100

                    HStack {
                        VStack(alignment: .leading) {
                            Text("Символов: \(entry.characterCount)")
                            Text("Изменение: \(deltaText)")
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
                            if let i = stage.entries.firstIndex(where: { $0.id == entry.id }) {
                                stage.entries.remove(at: i)
                            }
                            modelContext.delete(entry)
                        } label: {
                            Image(systemName: "trash")
                        }
                    }
                }
            }
            .padding()
        }
        .sheet(isPresented: $showingAddEntry) {
            AddStageEntryView(stage: stage)
        }
        .sheet(item: $editingEntry) { entry in
            EditEntryView(entry: entry)
        }
    }
}
