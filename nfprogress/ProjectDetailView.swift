#if canImport(SwiftUI)
import SwiftUI
import SwiftData

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    #if os(macOS)
    @Environment(\.openWindow) private var openWindow
    #endif
    @Bindable var project: WritingProject
    @State private var showingAddEntry = false
    @State private var addEntryStage: Stage?
    @State private var editingEntry: Entry?
    @State private var editingStage: Stage?
    @State private var showingAddStage = false
    @State private var expandedStages: Set<Stage.ID> = []
    @State private var stageToDelete: Stage?
    @State private var tempDeadline: Date = Date()
    @State private var selectedEntry: Entry?
    // Editing state for individual fields
    @State private var isEditingTitle = false
    @State private var isEditingGoal = false
    @State private var isEditingDeadline = false
    @FocusState private var focusedField: Field?

    /// Отступ ячеек истории и этапов, масштабируемый относительно размера текста.
    @ScaledMetric private var baseRowPadding: CGFloat = 4
    @ScaledMetric private var baseViewSpacing: CGFloat = 16
    @Environment(\.textScale) private var textScale
    private var rowPadding: CGFloat { baseRowPadding * textScale }
    private var viewSpacing: CGFloat { baseViewSpacing * textScale }

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
        #if os(macOS)
        let request = AddEntryRequest(projectID: project.id, stageID: stage?.id)
        openWindow(id: "addEntry", value: request)
        #else
        if let stage {
            addEntryStage = stage
        } else {
            showingAddEntry = true
        }
        #endif
    }

    private func addStage() {
        #if os(macOS)
        let request = AddStageRequest(projectID: project.id)
        openWindow(id: "addStage", value: request)
        #else
        showingAddStage = true
        #endif
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: viewSpacing) {
                // Название, цель и дедлайн проекта
                Grid(alignment: .leading, horizontalSpacing: viewSpacing / 2, verticalSpacing: viewSpacing / 2) {
                    GridRow {
                        Text("Название:")
                            .font(.title3.bold())
                            .applyTextScale()
                        if isEditingTitle {
                            TextField("", text: $project.title)
                                .textFieldStyle(.roundedBorder)
                                .submitLabel(.done)
                                .focused($focusedField, equals: .title)
                                .onSubmit { focusedField = nil }
                        } else {
                            Text(project.title)
                                .applyTextScale()
                                .onTapGesture {
                                    isEditingTitle = true
                                    focusedField = .title
                                }
                        }
                    }

                    GridRow {
                        Text("Цель:")
                            .font(.title3.bold())
                            .applyTextScale()
                        if isEditingGoal {
                            TextField("", value: $project.goal, formatter: NumberFormatter())
                                .textFieldStyle(.roundedBorder)
                                .submitLabel(.done)
                                .focused($focusedField, equals: .goal)
                                .onSubmit { focusedField = nil }
                        } else {
                            Text("\(project.goal)")
                                .applyTextScale()
                                .onTapGesture {
                                    isEditingGoal = true
                                    focusedField = .goal
                                }
                        }
                    }

                    GridRow {
                        Text("Дедлайн:")
                            .font(.title3.bold())
                            .applyTextScale()
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
                            .applyTextScale()
                            .onTapGesture {
                                tempDeadline = project.deadline ?? Date()
                                isEditingDeadline = true
                                focusedField = .deadline
                            }
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
                        .applyTextScale()
                        .foregroundColor(deadlineColor(daysLeft: project.daysLeft))
                    if let target = project.dailyTarget {
                        Text("Ежедневная цель: \(target) символов")
                            .font(.title3.bold())
                            .applyTextScale()
                            .foregroundColor(.white)
                    }
                }

                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .applyTextScale()
                        .foregroundColor(.green)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .applyTextScale()
                        .foregroundColor(.green)
                }

                // Этапы
                Text("Этапы")
                    .font(.title3.bold())
                    .applyTextScale()
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
                                let cumulative = stage.sortedEntries.prefix(index + 1).reduce(0) { $0 + $1.characterCount }
                                let clamped = max(cumulative, 0)
                                let percent = Double(clamped) / Double(max(stage.goal, 1)) * 100

                                let delta = entry.characterCount
                                let deltaPercent = Double(delta) / Double(max(stage.goal, 1)) * 100
                                let deltaText = String(format: "%+d (%+.0f%%)", delta, deltaPercent)

                                let isSelected = selectedEntry?.id == entry.id

                                HStack {
                                    VStack(alignment: .leading) {
                                        Text("Символов: \(clamped)")
                                            .applyTextScale()
                                        Text(String(format: "Прогресс этапа: %.0f%%", percent))
                                            .applyTextScale()
                                            .foregroundColor(progressColor(percent / 100))
                                        Text("Изменение: \(deltaText)")
                                            .applyTextScale()
                                            .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                                        Text(entry.date.formatted(date: .numeric, time: .shortened))
                                            .applyTextScale()
                                            .font(.caption)
                                            .foregroundColor(.gray)
                                    }
                                    Spacer()
                                    if isSelected {
                                        Button {
#if os(macOS)
                                            let req = EditEntryRequest(projectID: project.id, entryID: entry.id)
                                            openWindow(id: "editEntry", value: req)
#else
                                            editingEntry = entry
#endif
                                        } label: { Image(systemName: "pencil") }
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
                                .contentShape(Rectangle())
                                .padding(rowPadding)
                                .background(isSelected ? Color.accentColor.opacity(0.2) : Color.clear)
                                .onTapGesture {
                                    if selectedEntry?.id == entry.id {
                                        selectedEntry = nil
                                    } else {
                                        selectedEntry = entry
                                    }
                                }
                            }
                        } label: {
                            StageHeaderView(
                                stage: stage,
                                project: project,
                                onEdit: { editingStage = stage },
                                onDelete: { stageToDelete = stage }
                            )
                        }
                    }
                }

                // История записей
                Text("История записей")
                    .font(.title3.bold())
                    .applyTextScale()
                if project.stages.isEmpty {
                    Button("Добавить запись") {
                        addEntry()
                    }
                    .keyboardShortcut("n", modifiers: .command)
                }
                if project.sortedEntries.count >= 2 {
                    DisclosureGroup(
                        isExpanded: Binding(
                            get: { !project.isChartCollapsed },
                            set: { project.isChartCollapsed = !$0 }
                        )
                    ) {
                        ProgressChartView(project: project)
                    } label: {
                        Text("График прогресса")
                            .font(.title3.bold())
                            .applyTextScale()
                    }
                }

                ForEach(project.sortedEntries) { entry in
                    let total = project.globalProgress(for: entry)
                    let prevCount = project.previousGlobalProgress(before: entry)
                    let delta = total - prevCount
                    let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
                    let deltaText = String(format: "%+d (%+.0f%%)", delta, deltaPercent)
                    let progressPercent = Double(total) / Double(max(project.goal, 1)) * 100
                    let stageName = project.stageForEntry(entry)?.title

                    let isSelected = selectedEntry?.id == entry.id

                    HStack {
                        VStack(alignment: .leading) {
                            if let stageName {
                                Text("Этап: \(stageName)")
                                    .font(.caption)
                                    .applyTextScale()
                            }
                            Text("Символов: \(total)")
                                .applyTextScale()
                            Text("Изменение: \(deltaText)")
                                .applyTextScale()
                                .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                            Text(String(format: "Прогресс: %.0f%%", progressPercent))
                                .applyTextScale()
                                .font(.caption)
                                .foregroundColor(.gray)
                            Text(entry.date.formatted(date: .numeric, time: .shortened))
                                .applyTextScale()
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                        Spacer()
                        if isSelected {
                            Button {
#if os(macOS)
                                let req = EditEntryRequest(projectID: project.id, entryID: entry.id)
                                openWindow(id: "editEntry", value: req)
#else
                                editingEntry = entry
#endif
                            } label: {
                                Image(systemName: "pencil")
                            }
                            Button(role: .destructive) {
                                if let stage = project.stageForEntry(entry) {
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
                    .contentShape(Rectangle())
                    .padding(rowPadding)
                    .background(isSelected ? Color.accentColor.opacity(0.2) : Color.clear)
                    .onTapGesture {
                        if selectedEntry?.id == entry.id {
                            selectedEntry = nil
                        } else {
                            selectedEntry = entry
                        }
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .simultaneousGesture(
            TapGesture().onEnded { focusedField = nil }
        )
        .onAppear {
            if let dl = project.deadline {
                tempDeadline = dl
            }
        }
        #if !os(macOS)
        .sheet(isPresented: $showingAddEntry) {
            AddEntryView(project: project)
        }
        .sheet(item: $addEntryStage) { stage in
            AddEntryView(project: project, stage: stage)
        }
        .sheet(isPresented: $showingAddStage) {
            AddStageView(project: project)
        }
        .sheet(item: $editingEntry) { entry in
            EditEntryView(project: project, entry: entry)
        }
        #endif
        .sheet(item: $editingStage) { stage in
            EditStageView(stage: stage)
        }
        .onReceive(NotificationCenter.default.publisher(for: .menuAddEntry)) { _ in
            addEntry()
        }
        .onReceive(NotificationCenter.default.publisher(for: .menuAddStage)) { _ in
            addStage()
        }
        .alert(item: $stageToDelete) { stage in
            if project.stages.count == 1 {
                return Alert(
                    title: Text("Удалить этап \"\(stage.title)\"?"),
                    message: Text("Записи из этого этапа будут перенесены в проект. Если вы хотите удалить их, нажмите кнопку \"Удалить полностью\"."),
                    primaryButton: .default(Text("Удалить и перенести")) {
                        deleteStage(stage, moveEntries: true)
                    },
                    secondaryButton: .destructive(Text("Удалить полностью")) {
                        deleteStage(stage, moveEntries: false)
                    }
                )
            } else {
                return Alert(
                    title: Text("Удалить этап \"\(stage.title)\"?"),
                    message: Text("Все записи из этапа будут удалены."),
                    primaryButton: .destructive(Text("Удалить")) { deleteStage(stage) },
                    secondaryButton: .cancel()
                )
            }
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
        // Removed project title from toolbar to declutter interface
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
    private func deleteStage(_ stage: Stage, moveEntries: Bool = false) {
        if moveEntries {
            project.entries.append(contentsOf: stage.entries)
        } else {
            for entry in stage.entries {
                modelContext.delete(entry)
            }
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

#endif
