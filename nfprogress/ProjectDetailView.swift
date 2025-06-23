#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
#if os(macOS)
    @Environment(\.openWindow) private var openWindow
#endif
    @EnvironmentObject private var settings: AppSettings
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

    /// Base spacing for history and stages sections.
    private let viewSpacing: CGFloat = scaledSpacing(2)
    /// Size for ``ProgressCircleView`` shown on iOS.
    private let circleSize: CGFloat = layoutStep(20)

    // Formatter for displaying deadline
    private var deadlineFormatter: DateFormatter {
        let df = DateFormatter()
        df.locale = settings.locale
        df.dateFormat = "d MMMM yyyy"
        return df
    }

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

    /// Image used for sharing the current progress circle.
    @MainActor private var shareItem: ShareableProgressImage? {
        guard let image = progressShareImage(for: project) else { return nil }
        return ShareableProgressImage(image: image)
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
            LazyVStack(alignment: .leading, spacing: scaledSpacing(1.5)) {
                // Название, цель и дедлайн проекта
                Grid(alignment: .leading, horizontalSpacing: viewSpacing / 2, verticalSpacing: viewSpacing / 2) {
                    GridRow {
                        Text("label_title_colon")
                            .font(.title3.bold())
                            .fixedSize(horizontal: false, vertical: true)
                        if isEditingTitle {
                            TextField("", text: $project.title)
                                .textFieldStyle(.roundedBorder)
                                .submitLabel(.done)
                                .focused($focusedField, equals: .title)
                                .onSubmit { focusedField = nil }
                        } else {
                            Text(project.title)
                                .fixedSize(horizontal: false, vertical: true)
                                .onTapGesture {
                                    isEditingTitle = true
                                    focusedField = .title
                                }
                        }
                    }

                    GridRow {
                        Text("label_goal_colon")
                            .font(.title3.bold())
                            .fixedSize(horizontal: false, vertical: true)
                        if isEditingGoal {
                            TextField("", value: $project.goal, formatter: NumberFormatter())
                                .textFieldStyle(.roundedBorder)
                                .submitLabel(.done)
                                .focused($focusedField, equals: .goal)
                                .onSubmit { focusedField = nil }
                        } else {
                            Text("\(project.goal)")
                                .fixedSize(horizontal: false, vertical: true)
                                .onTapGesture {
                                    isEditingGoal = true
                                    focusedField = .goal
                                }
                        }
                    }

                    GridRow {
                        Text("label_deadline_colon")
                            .font(.title3.bold())
                            .fixedSize(horizontal: false, vertical: true)
                        if isEditingDeadline {
                            DatePicker(
                                "",
                                selection: $tempDeadline,
                                displayedComponents: .date
                            )
                            .labelsHidden()
                            .environment(\.locale, settings.locale)
                            .focused($focusedField, equals: .deadline)
                            .submitLabel(.done)
                            .onSubmit { focusedField = nil }
                        } else {
                            Text(
                                project.deadline.map { deadlineFormatter.string(from: $0) } ??
                                    settings.localized("not_set")
                            )
                            .fixedSize(horizontal: false, vertical: true)
                            .onTapGesture {
                                tempDeadline = project.deadline ?? Date()
                                isEditingDeadline = true
                                focusedField = .deadline
                            }
                        }
                    }
                }

                if !isEditingDeadline && project.deadline != nil {
                    Button("remove_deadline", role: .destructive) {
                        project.deadline = nil
                        saveContext()
                    }

                    Text(settings.localized("days_left", project.daysLeft))
                        .font(.subheadline)
                        .fixedSize(horizontal: false, vertical: true)
                        .foregroundColor(deadlineColor(daysLeft: project.daysLeft))
                    if let target = project.dailyTarget {
                        Text(settings.localized("daily_goal", target))
                            .font(.title3.bold())
                            .foregroundColor(.white)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .foregroundColor(.green)
                        .fixedSize(horizontal: false, vertical: true)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .foregroundColor(.green)
                        .fixedSize(horizontal: false, vertical: true)
                }

#if os(iOS)
                HStack {
                    Spacer()
                    ProgressCircleView(project: project, trackProgress: false, style: .large)
                        .frame(width: circleSize, height: circleSize)
                    Spacer()
                }
#endif
                if project.sortedEntries.count >= 2 {
                    DisclosureGroup(
                        isExpanded: Binding(
                            get: { !project.isChartCollapsed },
                            set: { project.isChartCollapsed = !$0 }
                        )
                    ) {
                        ProgressChartView(project: project)
                            .environmentObject(settings)
                    } label: {
                        Text("progress_chart")
                            .font(.title3.bold())
                    }
                }



                // Этапы
                Text("stages")
                    .font(.title3.bold())
                    .fixedSize(horizontal: false, vertical: true)
                Button("add_stage") {
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
                                Button("add_entry_button") { addEntry(stage: stage) }
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
                                        Text(settings.localized("characters_count", clamped))
                                            .fixedSize(horizontal: false, vertical: true)
                                        Text(settings.localized("stage_progress_format", percent))
                                            .fixedSize(horizontal: false, vertical: true)
                                            .foregroundColor(progressColor(percent / 100))
                                        Text(settings.localized("change_format", delta, deltaPercent))
                                            .fixedSize(horizontal: false, vertical: true)
                                            .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                                        Text(entry.date.formatted(date: .numeric, time: .shortened))
                                            .fixedSize(horizontal: false, vertical: true)
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
                                .scaledPadding(1, .vertical)
                                .frame(minHeight: layoutStep(10))
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
                            .environmentObject(settings)
                        }
                    }
                }

                // История записей
                Text("entries_history")
                    .font(.title3.bold())
                if project.stages.isEmpty {
                    Button("add_entry_button") {
                        addEntry()
                    }
                    .keyboardShortcut("n", modifiers: .command)
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
                                Text(settings.localized("stage_colon", stageName))
                                    .font(.caption)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            Text(settings.localized("characters_count", total))
                                .fixedSize(horizontal: false, vertical: true)
                            Text(settings.localized("change_format", delta, deltaPercent))
                                .fixedSize(horizontal: false, vertical: true)
                                .foregroundColor(delta > 0 ? .green : (delta < 0 ? .red : .primary))
                            Text(settings.localized("progress_format", progressPercent))
                                .fixedSize(horizontal: false, vertical: true)
                                .font(.caption)
                                .foregroundColor(.gray)
                            Text(entry.date.formatted(date: .numeric, time: .shortened))
                                .fixedSize(horizontal: false, vertical: true)
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
                    .scaledPadding(1, .vertical)
                    .frame(minHeight: layoutStep(10))
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
            .scaledPadding()
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
                    title: Text(settings.localized("delete_stage_confirm", stage.title)),
                    message: Text("stage_delete_move_warning"),
                    primaryButton: .default(Text("delete_and_move")) {
                        deleteStage(stage, moveEntries: true)
                    },
                    secondaryButton: .destructive(Text("delete_completely")) {
                        deleteStage(stage, moveEntries: false)
                    }
                )
            } else {
                return Alert(
                    title: Text(settings.localized("delete_stage_confirm", stage.title)),
                    message: Text("stage_delete_warning"),
                    primaryButton: .destructive(Text("delete")) { deleteStage(stage) },
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
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                if let item = shareItem {
                    ShareLink(item: item) {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .help(settings.localized("share_progress_tooltip"))
                }
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
