import SwiftUI
import SwiftData

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

    var body: some View {
        VStack(spacing: 16) {
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

            DatePicker("date_time", selection: $entry.date)
                .labelsHidden()

            if !project.stages.isEmpty {
                Picker("stage", selection: $selectedStageIndex) {
                    ForEach(Array(project.stages.enumerated()), id: \.offset) { idx, stage in
                        Text(stage.title).tag(idx)
                    }
                }
                .labelsHidden()
            }

            TextField("characters", value: $editedCount, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 120)

            Spacer()

            Button("done") {
                saveChanges()
                dismiss()
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
        .onDisappear {
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
        .onChange(of: entry.date) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
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
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
    }

    private static func progressAfterEntry(project: WritingProject, entry: Entry) -> Int {
        if let stage = project.stageForEntry(entry) {
            let sorted = stage.sortedEntries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return entry.characterCount }
            return sorted.prefix(idx + 1).reduce(0) { $0 + $1.characterCount }
        } else {
            let sorted = project.entries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return entry.characterCount }
            return sorted.prefix(idx + 1).reduce(0) { $0 + $1.characterCount }
        }
    }

    private static func progressBeforeEntry(project: WritingProject, entry: Entry) -> Int {
        if let stage = project.stageForEntry(entry) {
            let sorted = stage.sortedEntries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return 0 }
            return sorted.prefix(idx).reduce(0) { $0 + $1.characterCount }
        } else {
            let sorted = project.entries.sorted { $0.date < $1.date }
            guard let idx = sorted.firstIndex(where: { $0.id == entry.id }) else { return 0 }
            return sorted.prefix(idx).reduce(0) { $0 + $1.characterCount }
        }
    }

    private func saveChanges() {
        let previous = Self.progressBeforeEntry(project: project, entry: entry)
        entry.characterCount = editedCount - previous
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
    }
}
