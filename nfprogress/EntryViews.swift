#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct AddEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    /// Этап, в который будет добавлена запись, если он указан.
    /// При его наличии выбор этапа скрывается, и запись автоматически назначается этому этапу.
    private let fixedStage: Stage?
    @State private var selectedStageIndex: Int

    @State private var date = Date()
    /// Текст, введённый пользователем для нового значения прогресса.
    @State private var characterText = ""

    /// Текущий прогресс выбранного этапа или всего проекта.
    private var previousProgress: Int {
        if let fixedStage {
            return fixedStage.currentProgress
        }
        if project.stages.isEmpty {
            return project.currentProgress
        }
        let stage = project.stages[min(max(selectedStageIndex, 0), project.stages.count - 1)]
        return stage.currentProgress
    }

    init(project: WritingProject, stage: Stage? = nil) {
        self.project = project
        self.fixedStage = stage
        let initialIndex: Int
        if let stage,
           let found = project.stages.firstIndex(where: { $0.id == stage.id }) {
            initialIndex = found
        } else {
            initialIndex = 0
        }
        _selectedStageIndex = State(initialValue: initialIndex)
    }

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(15)
    private let minWidth: CGFloat = layoutStep(35)
    private let minHeight: CGFloat = layoutStep(20)

    var body: some View {
        VStack(spacing: viewSpacing) {
            DatePicker("date_time", selection: $date)
                .labelsHidden()

            if fixedStage == nil && !project.stages.isEmpty {
                Picker("stage", selection: $selectedStageIndex) {
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title)
                            .tag(idx)
                    }
                }
                .labelsHidden()
            }

            SelectAllIntField(text: $characterText,
                              placeholder: "characters",
                              prompt: String(previousProgress),
                              focusOnAppear: true)
                .frame(width: fieldWidth)
                .submitLabel(.done)
                .onSubmit(addEntry)

            Spacer()

            Button("add") {
                addEntry()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            .scaledPadding(1, .bottom)
        }
        .scaledPadding(1, [.horizontal, .bottom])
        .scaledPadding(2, .top)
        .frame(minWidth: minWidth, minHeight: minHeight)
#if os(macOS)
        .onExitCommand { dismiss() }
#endif
        .onChange(of: selectedStageIndex) { newValue in
            guard fixedStage == nil,
                  project.stages.indices.contains(newValue) else { return }
            characterText = ""
        }
    }

    private func addEntry() {
        let targetStage: Stage?
        guard let entered = Int(characterText) else { return }
        let delta: Int
        if project.stages.isEmpty {
            targetStage = nil
            delta = entered - project.currentProgress
        } else {
            if let fixedStage {
                targetStage = fixedStage
            } else {
                let index = min(max(selectedStageIndex, 0), project.stages.count - 1)
                targetStage = project.stages[index]
            }
            delta = entered - (targetStage?.currentProgress ?? 0)
        }

        let newEntry = Entry(date: date, characterCount: delta)
        dismiss()
        DispatchQueue.main.async {
            if let stage = targetStage {
                stage.entries.append(newEntry)
            } else {
                project.entries.append(newEntry)
            }
            try? project.modelContext?.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        }
    }
}


import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct EditEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject
    @Bindable var entry: Entry
    @State private var selectedStageIndex: Int = 0
    @State private var editedCount: Int = 0

    init(project: WritingProject, entry: Entry) {
        self.project = project
        self.entry = entry
        if let stage = project.stageForEntry(entry),
           let idx = project.stages.firstIndex(where: { $0.id == stage.id }) {
            _selectedStageIndex = State(initialValue: idx)
        }
        _editedCount = State(initialValue: Self.progressAfterEntry(project: project, entry: entry))
    }

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(15)
    private let minWidth: CGFloat = layoutStep(40)
    private let minHeight: CGFloat = layoutStep(25)

    var body: some View {
        VStack(spacing: viewSpacing) {
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
            }

            Text("edit_entry")
                .font(.title2.bold())
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            DatePicker("date_time", selection: $entry.date)
                .labelsHidden()

            if !project.stages.isEmpty {
                Picker("stage", selection: $selectedStageIndex) {
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title)
                            .tag(idx)
                    }
                }
                .labelsHidden()
            }

            TextField("characters", value: $editedCount, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)

            Spacer()

            Button("done") {
                saveChanges()
                dismiss()
            }
            .buttonStyle(.borderedProminent)
            .scaledPadding(1, .bottom)
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
#if os(macOS)
        .onExitCommand { dismiss() }
#endif
        .onDisappear {
            NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        }
        .onChange(of: entry.date) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        }
        .onChange(of: selectedStageIndex) { newValue in
            guard !project.stages.isEmpty else { return }
            moveEntry(to: project.stages[newValue])
        }
    }

    private func moveEntry(to stage: Stage) {
        if let currentStage = project.stageForEntry(entry) {
            if let i = currentStage.entries.firstIndex(where: { $0.id == entry.id }) {
                currentStage.entries.remove(at: i)
            }
        } else if let idx = project.entries.firstIndex(where: { $0.id == entry.id }) {
            project.entries.remove(at: idx)
        }
        stage.entries.append(entry)
        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
    }

    private static func progressAfterEntry(project: WritingProject, entry: Entry) -> Int {
        if let stage = project.stageForEntry(entry) {
            let sorted = stage.sortedEntries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return entry.characterCount }
            return sorted.prefix(idx + 1).cumulativeProgress()
        } else {
            let sorted = project.entries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return entry.characterCount }
            return sorted.prefix(idx + 1).cumulativeProgress()
        }
    }

    private static func progressBeforeEntry(project: WritingProject, entry: Entry) -> Int {
        if let stage = project.stageForEntry(entry) {
            let sorted = stage.sortedEntries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return 0 }
            return sorted.prefix(idx).cumulativeProgress()
        } else {
            let sorted = project.entries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return 0 }
            return sorted.prefix(idx).cumulativeProgress()
        }
    }

    private func saveChanges() {
        let previous = Self.progressBeforeEntry(project: project, entry: entry)
        entry.characterCount = editedCount - previous
        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
    }
}


import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct MenuBarEntryView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    @Query private var projects: [WritingProject]

    @State private var selectedIndex: Int = 0
    @State private var selectedStageIndex: Int = 0
    /// Текст, введённый пользователем для нового значения прогресса.
    @State private var characterText: String = ""
    @State private var date: Date = .now
    @State private var didSave: Bool = false

    /// Предыдущий прогресс для выбранного этапа или проекта.
    private var previousProgress: Int {
        guard !projects.isEmpty else { return 0 }
        let project = projects[min(max(selectedIndex, 0), projects.count - 1)]
        if selectedStageIndex > 0 && selectedStageIndex - 1 < project.stages.count {
            return project.stages[selectedStageIndex - 1].currentProgress
        } else {
            return project.currentProgress
        }
    }

    private let viewSpacing: CGFloat = scaledSpacing(1)
    private let fieldWidth: CGFloat = layoutStep(20)
    private let minWidth: CGFloat = layoutStep(25)
    private let minHeight: CGFloat = layoutStep(20)

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
            }

            if projects.isEmpty {
                Text("no_projects")
            } else {
                Picker("project_picker", selection: $selectedIndex) {
                    ForEach(Array(projects.enumerated()), id: \.offset) { idx, project in
                        Text(project.title)
                            .tag(idx)
                    }
                }
                .labelsHidden()
                let project = projects[min(max(selectedIndex, 0), projects.count - 1)]
                if !project.stages.isEmpty {
                    Picker("stage_picker", selection: $selectedStageIndex) {
                        Text("no_stage")
                            .tag(0)
                        ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                            Text(stage.title)
                                .tag(idx + 1)
                        }
                    }
                    .labelsHidden()
                }
                TextField("characters_field", text: $characterText, prompt: Text(String(previousProgress)))
                    .textFieldStyle(.roundedBorder)
                    .frame(width: fieldWidth)
                    .onSubmit {
                        if maybeSave() { dismiss() }
                    }
                DatePicker("date_field", selection: $date)
                    .labelsHidden()
                Button("add_button") {
                    if maybeSave() { dismiss() }
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
        .onDisappear {
            _ = maybeSave()
        }
        .onAppear {
            didSave = false
        }
        .onChange(of: selectedIndex) { _ in
            selectedStageIndex = 0
        }
    }

    private func maybeSave() -> Bool {
        guard !didSave, isValid else { return false }
        let index = min(max(selectedIndex, 0), projects.count - 1)
        let project = projects[index]

        let entry: Entry
        if selectedStageIndex > 0 && selectedStageIndex - 1 < project.stages.count {
            let stage = project.stages[selectedStageIndex - 1]
            // Преобразуем введённый прогресс в дельту относительно выбранного этапа
            guard let value = Int(characterText) else { return false }
            let delta = value - stage.currentProgress
            entry = Entry(date: date, characterCount: delta)
            stage.entries.append(entry)
        } else {
            guard let value = Int(characterText) else { return false }
            let delta = value - project.currentProgress
            entry = Entry(date: date, characterCount: delta)
            project.entries.append(entry)
        }
        try? modelContext.save()
        didSave = true
        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        resetFields()
        return true
    }

    private var isValid: Bool {
        !projects.isEmpty && Int(characterText) != nil
    }

    private func resetFields() {
        characterText = ""
        date = .now
        selectedStageIndex = 0
    }
}

#endif
