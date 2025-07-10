
#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif
#if canImport(AppKit)
import AppKit
#endif


@MainActor
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
    @State private var draggedStage: Stage?
    @State private var dropTargetStage: Stage?
    // Состояние редактирования отдельных полей
    @State private var isEditingGoal = false
    @State private var isEditingDeadline = false
    @FocusState private var focusedField: Field?
#if os(iOS)
    @State private var showingSharePreview = false
#endif

    /// Базовый отступ между секциями истории и этапов.
    private let viewSpacing: CGFloat = scaledSpacing(2)
    /// Размер ``ProgressCircleView`` на iOS.
    private let circleSize: CGFloat = layoutStep(20)

    // Форматтер для отображения дедлайна
    private var deadlineFormatter: DateFormatter {
        let df = DateFormatter()
        df.locale = settings.locale
        df.dateFormat = "d MMMM yyyy"
        return df
    }

    private enum Field: Hashable {
        case goal, deadline
    }

    private func deadlineColor(daysLeft: Int) -> Color {
        let maxDays = 30.0
        let ratio = max(0, min(1, Double(daysLeft) / maxDays))
        // Оттенок от красного (0) к зелёному (0.33)
        let hue = ratio * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    private func progressColor(_ percent: Double) -> Color {
        let clamped = max(0, min(1, percent))
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

#if os(iOS)
    @ViewBuilder
    private var progressCircleSection: some View {
        HStack {
            Spacer()
            ProgressCircleView(project: project, trackProgress: false, style: .large)
                .id(project.id)
                .frame(width: circleSize, height: circleSize)
            Spacer()
        }
    }
#else
    @ViewBuilder
    private var progressCircleSection: some View { EmptyView() }
#endif

    @ViewBuilder
    private var chartSection: some View {
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
    }

    @ViewBuilder
    private var stagesSection: some View {
        Text("stages")
            .font(.title3.bold())
            .fixedSize(horizontal: false, vertical: true)
        Button("add_stage") { addStage() }
        if !project.stages.isEmpty {
            ForEach(project.stages.sorted { $0.order < $1.order }) { stage in
                stageDisclosureView(for: stage)
                    .onDrag {
                        draggedStage = stage
                        dropTargetStage = nil
                        return NSItemProvider(object: NSString(string: stage.title))
                    }
                    .onDrop(of: [.text], delegate: StageDropDelegate(
                        target: stage,
                        draggedItem: $draggedStage,
                        lastTarget: $dropTargetStage,
                        getStages: { project.stages.sorted { $0.order < $1.order } },
                        moveAction: moveStages
                    ))
            }
        }
    }

    @ViewBuilder
    private func stageDisclosureView(for stage: Stage) -> some View {
        DisclosureGroup(
            isExpanded: Binding(
                get: { expandedStages.contains(stage.id) },
                set: { newValue in
                    if newValue { expandedStages.insert(stage.id) } else { expandedStages.remove(stage.id) }
                }
            )
        ) {
            StageEntriesView(
                project: project,
                stage: stage,
                selectedEntry: $selectedEntry,
                editingEntry: $editingEntry,
                addEntryAction: { addEntry(stage: $0) }
            )
            .environmentObject(settings)
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

    /// Список записей для конкретного этапа
    private struct StageEntriesView: View {
        @Environment(\.modelContext) private var modelContext
        @EnvironmentObject private var settings: AppSettings
        @Bindable var project: WritingProject
        @Bindable var stage: Stage
        @Binding var selectedEntry: Entry?
        @Binding var editingEntry: Entry?
        var addEntryAction: (Stage) -> Void

#if os(macOS)
        @Environment(\.openWindow) private var openWindow
#endif

        var body: some View {
            VStack(alignment: .leading) {
                HStack {
                    Button("add_entry_button") { addEntryAction(stage) }
#if os(macOS)
                    Button("sync_now_button") {
                        DocumentSyncManager.syncNow(stage: stage)
                    }
                    .disabled(stage.syncType == nil)
#endif
                    Spacer()
                }
                ForEach(stage.sortedEntries) { entry in
                    entryRow(entry: entry)
                }
            }
        }

        private func entryRow(entry: Entry) -> some View {
            let index = stage.sortedEntries.firstIndex(where: { $0.id == entry.id }) ?? 0
            let cumulative = stage.sortedEntries.prefix(index + 1).cumulativeProgress()
            let clamped = max(cumulative, 0)
            let percent = Double(clamped) / Double(max(stage.goal, 1)) * 100

            let previous = stage.sortedEntries.prefix(index).cumulativeProgress()
            let delta = cumulative - previous
            let deltaPercent = Double(delta) / Double(max(stage.goal, 1)) * 100

            let isSelected = selectedEntry?.id == entry.id

            return HStack {
                if entry.syncSource == .word {
                    Image(systemName: "doc")
                } else if entry.syncSource == .scrivener {
                    Image(systemName: "doc.text")
                }
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
                        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
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

        private func progressColor(_ percent: Double) -> Color {
            let clamped = max(0, min(1, percent))
            let hue = clamped * 0.33
            return Color(hue: hue, saturation: 1, brightness: 1)
        }

        private func saveContext() {
            do {
                try modelContext.save()
            } catch {
                print("Ошибка сохранения: \(error)")
            }
        }
    }


    @ViewBuilder
    private var historySection: some View {
        Text("entries_history")
            .font(.title3.bold())
        if project.stages.isEmpty {
            HStack {
                Button("add_entry_button") { addEntry() }
                    .keyboardShortcut("n", modifiers: .command)
#if os(macOS)
                Button("sync_now_button") {
                    DocumentSyncManager.syncNow(project: project)
                }
                .disabled(project.syncType == nil)
#endif
                Spacer()
            }
        }
        ForEach(project.sortedEntries) { entry in
            historyEntryRow(entry: entry)
        }
    }

    @ViewBuilder
    private func historyEntryRow(entry: Entry) -> some View {
        let total = project.globalProgress(for: entry)
        let prevCount = project.previousGlobalProgress(before: entry)
        let delta = total - prevCount
        let deltaPercent = Double(delta) / Double(max(project.goal, 1)) * 100
        let progressPercent = Double(total) / Double(max(project.goal, 1)) * 100
        let stageName = project.stageForEntry(entry)?.title

        let isSelected = selectedEntry?.id == entry.id

        HStack {
            if entry.syncSource == .word {
                Image(systemName: "doc")
            } else if entry.syncSource == .scrivener {
                Image(systemName: "doc.text")
            }
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
                    NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
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

    private func shareToolbarButton() -> some View {
#if os(macOS)
        Button(action: {
            let request = SharePreviewRequest(projectID: project.id)
            openWindow(id: "sharePreview", value: request)
        }) {
            Image(systemName: "square.and.arrow.up")
        }
        .help(settings.localized("share_progress_tooltip"))
#else
        Button(action: { showingSharePreview = true }) {
            Image(systemName: "square.and.arrow.up")
        }
        .help(settings.localized("share_progress_tooltip"))
#endif
    }

#if os(macOS)
    private func wordSyncToolbarButton() -> some View {
        Button(action: { selectSyncFile() }) {
            Image(systemName: "arrow.triangle.2.circlepath")
        }
        .help(settings.localized("sync_document_tooltip"))
    }

    private func selectSyncFile() {
        if project.syncType != nil {
            let request = SyncInfoRequest(projectID: project.id)
            openWindow(id: "syncInfo", value: request)
            return
        }

        let alert = NSAlert()
        alert.messageText = settings.localized("sync_type_prompt")
        alert.addButton(withTitle: settings.localized("sync_type_word"))
        alert.addButton(withTitle: settings.localized("sync_type_scrivener"))
        let result = alert.runModal()
        switch result {
        case .alertFirstButtonReturn:
            let panel = NSOpenPanel()
            panel.allowedFileTypes = ["doc", "docx"]
            panel.allowsMultipleSelection = false
            if panel.runModal() == .OK, let url = panel.url {
                if DocumentSyncManager.isWordFileInUse(url.path, excludingProject: project.id) {
                    let alert = NSAlert()
                    alert.messageText = settings.localized("sync_already_linked")
                    alert.runModal()
                    return
                }
                project.syncType = .word
                project.wordFilePath = url.path
                project.wordFileBookmark = try? url.bookmarkData(options: .withSecurityScope)
                try? project.modelContext?.save()
                DocumentSyncManager.startMonitoring(project: project)
            }
        case .alertSecondButtonReturn:
            let panel = NSOpenPanel()
            panel.allowedFileTypes = ["scriv"]
            panel.canChooseFiles = true
            panel.canChooseDirectories = false
            panel.allowsMultipleSelection = false
            if panel.runModal() == .OK, let url = panel.url {
                selectScrivenerItem(projectURL: url)
            }
        default:
            break
        }
    }

    private func selectScrivenerItem(projectURL: URL) {
        let items = ScrivenerParser.items(in: projectURL)
        guard !items.isEmpty else {
            let alert = NSAlert()
            alert.messageText = settings.localized("scrivener_parse_error")
            alert.runModal()
            return
        }

        let request = ScrivenerSelectRequest(projectID: project.id, projectPath: projectURL.path)
        openWindow(id: "selectScrivenerItem", value: request)
    }
#endif

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

    @ViewBuilder
    private var infoSection: some View {
        // Название, цель и дедлайн проекта
        Grid(alignment: .leading, horizontalSpacing: viewSpacing / 2, verticalSpacing: viewSpacing / 2) {

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
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: scaledSpacing(1.5)) {
                infoSection
                progressCircleSection
                chartSection
                stagesSection
                historySection
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
#if os(macOS)
            if project.syncType != nil {
                DocumentSyncManager.startMonitoring(project: project)
            }
#endif
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
        .toolbar {
            ToolbarItem(placement: .principal) {
                ProjectTitleBar(project: project)
            }
            ToolbarItem(placement: .primaryAction) {
                shareToolbarButton()
            }
#if os(macOS)
            if !project.hasStageSync {
                ToolbarItem(placement: .primaryAction) {
                    wordSyncToolbarButton()
                }
            }
#endif
        }
        .navigationTitle("")
#if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
#endif
        .modifier(SyncSheetsModifier(
            project: project,
            showingAddEntry: $showingAddEntry,
            addEntryStage: $addEntryStage,
            showingAddStage: $showingAddStage,
            editingEntry: $editingEntry,
            editingStage: $editingStage
        ))
#if os(iOS)
        .sheet(isPresented: $showingSharePreview) {
            ProgressSharePreview(project: project)
                .environmentObject(settings)
                .presentationDetents([.medium, .large])
        }
#endif
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
            for (idx, st) in project.stages.enumerated() {
                st.order = idx
            }
        }
        // Удаляем возможную ссылку на удаляемый этап
        if draggedStage?.id == stage.id {
            draggedStage = nil
        }
        modelContext.delete(stage)
        saveContext()
        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
    }

    private func moveStages(from source: IndexSet, to destination: Int) {
        var updated = project.stages
        updated.move(fromOffsets: source, toOffset: destination)
        project.stages = updated
        for (index, stage) in project.stages.enumerated() {
            stage.order = index
        }
        try? modelContext.save()
    }

    // MARK: - Sheet Modifier
    private struct SyncSheetsModifier: ViewModifier {
        @Bindable var project: WritingProject
        @Binding var showingAddEntry: Bool
        @Binding var addEntryStage: Stage?
        @Binding var showingAddStage: Bool
        @Binding var editingEntry: Entry?
        @Binding var editingStage: Stage?

        func body(content: Content) -> some View {
#if os(macOS)
            content
                .sheet(item: $editingStage) { stage in
                    EditStageView(stage: stage, project: project)
                }
#else
            content
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
                .sheet(item: $editingStage) { stage in
                    EditStageView(stage: stage, project: project)
                }
#endif
        }
    }

    private struct StageDropDelegate: DropDelegate {
        let target: Stage
        @Binding var draggedItem: Stage?
        @Binding var lastTarget: Stage?
        /// Актуальный список этапов
        var getStages: () -> [Stage]
        /// Действие по перемещению этапов
        let moveAction: (IndexSet, Int) -> Void

        func dropEntered(info: DropInfo) {
            if lastTarget?.id == target.id { return }
            lastTarget = target

            let stages = getStages()
            guard let dragged = draggedItem,
                  dragged != target,
                  let from = stages.firstIndex(where: { $0.id == dragged.id }),
                  let to = stages.firstIndex(where: { $0.id == target.id }) else { return }
            // Перетаскиваемый этап должен занять позицию цели,
            // смещая её и последующие элементы вниз
            moveAction(IndexSet(integer: from), to)
        }

        func dropUpdated(info: DropInfo) -> DropProposal? {
            DropProposal(operation: .move)
        }

        func performDrop(info: DropInfo) -> Bool {
            draggedItem = nil
            lastTarget = nil
            return true
        }
    }
}

#endif
