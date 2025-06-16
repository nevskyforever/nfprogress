import SwiftUI
import SwiftData

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject
    @State private var showingAddEntry = false
    @State private var editingEntry: Entry?
    @State private var tempDeadline: Date = Date()
    // Editing state for individual fields
    @State private var isEditingTitle = true
    @State private var isEditingGoal = true
    @State private var isEditingDeadline = false
    @FocusState private var focusedField: Field?

    // Formatter for displaying deadline in Russian
    private let deadlineFormatter: DateFormatter = {
        let df = DateFormatter()
        df.locale = Locale(identifier: "ru_RU")
        df.dateFormat = "d MMMM yyyy"
        return df
    }()

    private enum Field: Hashable {
        case title, goal, deadline
    }

    private func deadlineColor(daysLeft: Int) -> Color {
        let maxDays = 30.0
        let ratio = max(0, min(1, Double(daysLeft) / maxDays))
        // Hue from red (0) to green (0.33)
        let hue = ratio * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Название и цель проекта
                HStack {
                    Text("Название:")
                    if isEditingTitle {
                        TextField("", text: $project.title)
                            .textFieldStyle(.roundedBorder)
                            .fixedSize()
                            .submitLabel(.done)
                            .focused($focusedField, equals: .title)
                            .onSubmit { focusedField = nil }
                    } else {
                        Text(project.title)
                            .onTapGesture {
                                isEditingTitle = true
                                focusedField = .title
                            }
                    }
                }
                HStack {
                    Text("Цель:")
                    if isEditingGoal {
                        TextField("", value: $project.goal, formatter: NumberFormatter())
                            .textFieldStyle(.roundedBorder)
                            .fixedSize()
                            .submitLabel(.done)
                            .focused($focusedField, equals: .goal)
                            .onSubmit { focusedField = nil }
                    } else {
                        Text("\(project.goal)")
                            .onTapGesture {
                                isEditingGoal = true
                                focusedField = .goal
                            }
                    }
                }

                // Дедлайн
                if isEditingDeadline {
                    HStack {
                        DatePicker("Дедлайн:", selection: $tempDeadline, displayedComponents: .date)
                            .environment(\.locale, Locale(identifier: "ru_RU"))
                            .focused($focusedField, equals: .deadline)
                            .onSubmit { focusedField = nil }
                        Button("Готово") {
                            focusedField = nil
                        }
                        if project.deadline != nil {
                            Button(role: .destructive) {
                                project.deadline = nil
                                focusedField = nil
                            } label: {
                                Text("Удалить")
                            }
                        }
                    }
                } else {
                    if let deadline = project.deadline {
                        HStack {
                            Text("Дедлайн:")
                            Text(deadlineFormatter.string(from: deadline))
                        }
                        .onTapGesture {
                            tempDeadline = deadline
                            isEditingDeadline = true
                            focusedField = .deadline
                        }

                        Text("Осталось дней: \(project.daysLeft)")
                            .font(.subheadline)
                            .foregroundColor(deadlineColor(daysLeft: project.daysLeft))
                        if let target = project.dailyTarget {
                            Text("Ежедневная цель: \(target) символов")
                                .font(.subheadline)
                                .foregroundColor(.white)
                        }
                    } else {
                        Text("Добавить дедлайн")
                            .foregroundColor(.accentColor)
                            .onTapGesture {
                                tempDeadline = Date()
                                isEditingDeadline = true
                                focusedField = .deadline
                            }
                    }
                }

                // Действия с проектом
                HStack {
                    Button("Добавить запись") {
                        showingAddEntry = true
                    }
                    Spacer()
                }

                // История записей
                Text("История записей")
                    .font(.headline)
                ProgressChartView(project: project)

                ForEach(project.sortedEntries) { entry in
                    let index = project.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
                    let prevCount = index > 0 ? project.sortedEntries[index - 1].characterCount : 0
                    let delta = entry.characterCount - prevCount
                    let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
                    let deltaText = String(format: "%+d (%+.0f%%)", delta, deltaPercent)
                    let progressPercent = Double(entry.characterCount) / Double(max(project.goal, 1)) * 100

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
                            if let i = project.entries.firstIndex(where: { $0.id == entry.id }) {
                                project.entries.remove(at: i)
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
        .onChange(of: focusedField) { newValue in
            if newValue != .title && isEditingTitle {
                isEditingTitle = false
                saveContext()
            }
            if newValue != .goal && isEditingGoal {
                isEditingGoal = false
                saveContext()
            }
            if newValue != .deadline && isEditingDeadline {
                project.deadline = tempDeadline
                isEditingDeadline = false
                saveContext()
            }
        }
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

