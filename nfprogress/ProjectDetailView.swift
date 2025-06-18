import SwiftUI
import SwiftData

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject
    @State private var showingAddEntry = false
    @State private var addEntryStage: Stage?
    @State private var editingEntry: Entry?
    @State private var editingStage: Stage?
    @State private var showingAddStage = false
    @State private var expandedStages: Set<Stage.ID> = []
    @State private var stageToDelete: Stage?
    @State private var tempDeadline: Date = Date()
    // Editing state for individual fields
    @State private var isEditingTitle = false
    @State private var isEditingGoal = false
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

    private func progressColor(_ percent: Double) -> Color {
        let clamped = max(0, min(1, percent))
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    private func addEntry(stage: Stage? = nil) {
        addEntryStage = stage
        showingAddEntry = true
    }

    private func addStage() {
        showingAddStage = true
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Название и цель проекта
                HStack {
                    Text("Название:")
                        .font(.title3.bold())
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
                        .font(.title3.bold())
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
                HStack {
                    Text("Дедлайн:")
                        .font(.title3.bold())
                    if isEditingDeadline {
                        DatePicker(
                            "",
                            selection: $tempDeadline,
                            displayedComponents: .date
                        )
                        .labelsHidden()
                        .environment(\.locale, Locale(identifier: "ru_RU"))
                        .focused($focusedField, equals: .deadline)
                        .submitLabel(.done)
                        .onSubmit { focusedField = nil }
                    } else {
                        Text(
                            project.deadline.map { deadlineFormatter.string(from: $0) } ??
                                "Не установлен"
                        )
                        .onTapGesture {
                            tempDeadline = project.deadline ?? Date()
                            isEditingDeadline = true
                            focusedField = .deadline
                        }
                    }
                }

                if !isEditingDeadline && project.deadline != nil {
                    Button("Удалить дедлайн", role: .destructive) {
                        project.deadline = nil
                        saveContext()
                    }

                    Text("Осталось дней: \(project.daysLeft)")
                        .font(.subheadline)
                        .foregroundColor(deadlineColor(daysLeft: project.daysLeft))
                    if let target = project.dailyTarget {
                        Text("Ежедневная цель: \(target) символов")
                            .font(.title3.bold())
                            .foregroundColor(.white)
                    }
                }

                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .foregroundColor(.green)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .foregroundColor(.green)
                }

                // Этапы
                Text("Этапы")
                    .font(.title3.bold())
                Button("Добавить этап") {
                    addStage()
                }
                if !project.stages.isEmpty {
                    ForEach(project.stages) { stage in
                        DisclosureGroup(
                            isExpanded: Binding(
                                get: { expandedStages.contains(stage.id) },
                                set: { newValue in
                                    if newValue { expandedStages.insert(stage.id) } else { expandedStages.remove(stage.id) }
                                }
                            )
                        ) {
                            HStack {
                                Button("Добавить запись") { addEntry(stage: stage) }
                                Spacer()
                            }
                            ForEach(stage.sortedEntries) { entry in
                                let index = stage.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
                                let prev = index > 0 ? stage.sortedEntries[index - 1].characterCount : stage.startProgress
                                let delta = entry.characterCount - prev
                                let percent = Double(entry.characterCount - stage.startProgress) / Double(max(stage.goal,1)) * 100
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text("Символов: \(entry.characterCount - stage.startProgress)")
                                        Text(String(format: "Прогресс этапа: %.0f%%", percent))
                                            .foregroundColor(progressColor(percent / 100))
                                        Text(entry.date.formatted(date: .numeric, time: .shortened))
                                            .font(.caption)
                                            .foregroundColor(.gray)
                                    }
                                    Spacer()
                                    Button { editingEntry = entry } label: { Image(systemName: "pencil") }
                                    Button(role: .destructive) {
                                        if let i = stage.entries.firstIndex(where: { $0.id == entry.id }) {
                                            stage.entries.remove(at: i)
                                        }
                                        modelContext.delete(entry)
                                        saveContext()
                                        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
                                    } label: { Image(systemName: "trash") }
                                }
                            }
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(stage.title)
                                    Text("Цель: \(stage.goal) знаков")
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                }
                                Spacer()
                                Text(String(format: "%.0f%%", stage.progressPercentage * 100))
                                    .foregroundColor(progressColor(stage.progressPercentage))
                                Button {
                                    editingStage = stage
                                } label: {
                                    Image(systemName: "pencil")
                                }
                                Button {
                                    stageToDelete = stage
                                } label: {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.borderless)
                            }
                            .font(.headline)
                        }
                    }
                }

                // История записей
                Text("История записей")
                    .font(.title3.bold())
                Button("Добавить запись") {
                    addEntry()
                }
                .keyboardShortcut("n", modifiers: .command)
                ProgressChartView(project: project)

                ForEach(project.sortedEntries) { entry in
                    let index = project.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
                    let prevCount = index > 0 ? project.sortedEntries[index - 1].characterCount : 0
                    let delta = entry.characterCount - prevCount
                    let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
                    let deltaText = String(format: "%+d (%+.0f%%)", delta, deltaPercent)
                    let progressPercent = Double(entry.characterCount) / Double(max(project.goal, 1)) * 100
                    let stageName = stageForEntry(entry)?.title

                    HStack {
                        VStack(alignment: .leading) {
                            if let stageName {
                                Text("Этап: \(stageName)")
                                    .font(.caption)
                            }
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
                            if let stage = stageForEntry(entry) {
                                if let i = stage.entries.firstIndex(where: { $0.id == entry.id }) {
                                    stage.entries.remove(at: i)
                                }
                            } else if let i = project.entries.firstIndex(where: { $0.id == entry.id }) {
                                project.entries.remove(at: i)
                            }
                            modelContext.delete(entry)
                            saveContext()
                            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
                        } label: {
                            Image(systemName: "trash")
                        }
                    }
                }
            }
            .padding()
        }
        .simultaneousGesture(
            TapGesture().onEnded { focusedField = nil }
        )
        .onAppear {
            if let dl = project.deadline {
                tempDeadline = dl
            }
        }
        .sheet(isPresented: $showingAddEntry) {
            AddEntryView(project: project, stage: addEntryStage)
        }
        .sheet(isPresented: $showingAddStage) {
            AddStageView(project: project)
        }
        .sheet(item: $editingEntry) { entry in
            EditEntryView(entry: entry)
        }
        .sheet(item: $editingStage) { stage in
            EditStageView(stage: stage)
        }
        .alert(item: $stageToDelete) { stage in
            Alert(
                title: Text("Удалить этап \"\(stage.title)\"?"),
                message: Text("Все записи из этапа будут удалены."),
                primaryButton: .destructive(Text("Удалить")) { deleteStage(stage) },
                secondaryButton: .cancel()
            )
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

    // MARK: - Helpers
    private func stageForEntry(_ entry: Entry) -> Stage? {
        for stage in project.stages {
            if stage.entries.contains(where: { $0.id == entry.id }) {
                return stage
            }
        }
        return nil
    }

    private func deleteStage(_ stage: Stage) {
        for entry in stage.entries {
            modelContext.delete(entry)
        }
        stage.entries.removeAll()
        if let index = project.stages.firstIndex(where: { $0.id == stage.id }) {
            project.stages.remove(at: index)
        }
        modelContext.delete(stage)
        saveContext()
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
    }
}

