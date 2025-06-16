import SwiftUI
import SwiftData

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject
    @State private var showingAddEntry = false
    @State private var editingEntry: Entry?
    @State private var tempDeadline: Date = Date()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Название и цель проекта
                TextField("Название проекта", text: $project.title)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                TextField("Цель (число)", value: $project.goal, formatter: NumberFormatter())
                    .textFieldStyle(RoundedBorderTextFieldStyle())

                // Дедлайн (сохраняется автоматически при изменении)
                DatePicker("Дедлайн", selection: $tempDeadline, displayedComponents: .date)
                    .labelsHidden()
                    .onChange(of: tempDeadline) { newDate in
                        project.deadline = newDate
                        saveContext()
                    }

                // Действия с проектом
                HStack {
                    Button("Добавить запись") {
                        showingAddEntry = true
                    }
                    Spacer()
                    // Кнопка удаления проекта
                    Button(role: .destructive) {
                        withAnimation {
                            modelContext.delete(project)
                            saveContext()
                        }
                    } label: {
                        Label("Удалить проект", systemImage: "trash")
                    }
                }

                // История записей
                Text("История записей")
                    .font(.headline)
                ProgressChartView(project: project)

                ForEach(project.sortedEntries) { entry in
                    let index = project.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
                    let prevCount = index > 0 ? project.sortedEntries[index - 1].characterCount : 0
                    let delta = entry.characterCount - prevCount
                    let deltaText = prevCount > 0
                        ? String(format: "%+d (%+.0f%%)", delta, Double(delta) / Double(prevCount) * 100)
                        : String(format: "%+d", delta)

                    HStack {
                        VStack(alignment: .leading) {
                            Text("Символов: \(entry.characterCount)")
                            Text("Изменение: \(deltaText)")
                                .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                            Text(entry.date.formatted(date: .omitted, time: .shortened))
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                        Spacer()
                        Button { editingEntry = entry } label: {
                            Image(systemName: "pencil")
                        }
                        Button(role: .destructive) {
                            if let idx = project.entries.firstIndex(where: { $0.id == entry.id }) {
                                project.entries.remove(at: idx)
                            }
                            modelContext.delete(entry)
                            saveContext()
                        } label: {
                            Image(systemName: "trash")
                        }
                    }
                }
            }
            .padding()
        }
        .onAppear {
            if let dl = project.deadline {
                tempDeadline = dl
            }
        }
        .sheet(isPresented: $showingAddEntry) {
            AddEntryView(project: project)
        }
        .sheet(item: $editingEntry) { entry in
            EditEntryView(entry: entry)
        }
        .onChange(of: project.title) { _ in saveContext() }
        .onChange(of: project.goal) { _ in saveContext() }
    }

    // MARK: - Save Context
    private func saveContext() {
        do {
            try modelContext.save()
        } catch {
            print("Ошибка сохранения: \(error)")
        }
    }
}

