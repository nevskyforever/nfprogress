#if canImport(SwiftUI)
import SwiftUI
#if os(macOS)
import AppKit
#endif
#if canImport(SwiftData)
import SwiftData
#endif

struct AddStageView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    @State private var title = ""
    @State private var goal = 1000

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(25)
    private let minWidth: CGFloat = layoutStep(35)
    private let minHeight: CGFloat = layoutStep(20)

    private var moveWarning: Bool {
        project.stages.isEmpty && !project.entries.isEmpty
    }

    var body: some View {
        VStack(spacing: viewSpacing) {
            TextField("project_name", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)
            TextField("project_goal", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)
            if moveWarning {
                Text(settings.localized("all_entries_move"))
                    .multilineTextAlignment(.center)
                    .foregroundColor(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
            Button("create") { addStage() }
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
    }

    private func addStage() {
        let name = title.isEmpty ? settings.localized("stage_placeholder") : title
        let start = (project.stages.isEmpty && !project.entries.isEmpty) ? 0 : project.currentProgress
        let stage = Stage(title: name, goal: goal, startProgress: start)
        let moveEntries = project.stages.isEmpty && !project.entries.isEmpty
        dismiss()
        DispatchQueue.main.async {
            if moveEntries {
                stage.entries = project.entries
                project.entries.removeAll()
            }
            project.stages.append(stage)
            try? project.modelContext?.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        }
    }
}



import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct EditStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var stage: Stage
    @Bindable var project: WritingProject

    private let viewSpacing: CGFloat = scaledSpacing(2)
    private let fieldWidth: CGFloat = layoutStep(25)
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

            Text("edit_stage")
                .font(.title2.bold())
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            TextField("project_name", text: $stage.title)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)

            TextField("project_goal", value: $stage.goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: fieldWidth)

            Spacer()

            Button("done") {
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
        .onChange(of: stage.goal) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
        }
    }
}


import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

/// Заголовок этапа с анимированным отображением процента прогресса
struct StageHeaderView: View {
    @EnvironmentObject private var settings: AppSettings
    @Bindable var stage: Stage
    @Bindable var project: WritingProject
    var onEdit: () -> Void
    var onDelete: () -> Void
#if os(macOS)
    @Environment(\.openWindow) private var openWindow
#endif

    /// Значение прогресса в начале анимации
    @State private var startProgress: Double = 0
    /// Целевое значение прогресса
    @State private var endProgress: Double = 0

    /// Минимальная и максимальная длительность анимации прогресса
    private let minDuration = 0.25
    private let maxDuration = 3.0

    /// Длительность текущей анимации
    @State private var duration: Double = 0.25

    /// Преобразует значение прогресса (0...1) в оттенок от красного к зелёному
    private func color(for percent: Double) -> Color {
        let clamped = max(0, min(1, percent))
        let hue = clamped * 0.33 // 0 = красный, 0.33 = зелёный
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    /// Текущий процент прогресса для этапа по количеству символов
    private var progress: Double {
        guard stage.goal > 0 else { return 0 }
        let percent = Double(stage.currentProgress) / Double(stage.goal)
        return min(max(percent, 0), 1.0)
    }

    /// Обновляет параметры анимации прогресса
    private func updateProgress(to newValue: Double) {
        // Пропускаем обновления, не изменяющие прогресс, чтобы не сбрасывать анимацию
        guard abs(newValue - endProgress) > 0.0001 else { return }

        startProgress = endProgress
        endProgress = newValue

        let diff = abs(endProgress - startProgress)
        let range = max(diff, 0.01)
        let scaled = min(range, 1.0)
        duration = min(minDuration + scaled * (maxDuration - minDuration), maxDuration)
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(stage.title)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .layoutPriority(1)
                Text(settings.localized("goal_characters", stage.goal))
                    .font(.caption)
                    .foregroundColor(.gray)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer()

            if #available(macOS 12, *) {
                AnimatedProgressView(
                    startPercent: startProgress,
                    endPercent: endProgress,
                    startColor: color(for: startProgress),
                    endColor: color(for: endProgress),
                    duration: duration
                ) { value, color in
                    let percent = Int(ceil(value * 100))
                    return ZStack {
                        Text("\(percent)%")
                            .monospacedDigit()
                            .bold()
                            .foregroundColor(color)
                    }
                }
            } else {
                AnimatedCounterText(value: endProgress, token: .progressValue)
                    .foregroundColor(color(for: endProgress))
            }
#if os(macOS)
            Button(action: { selectSyncFile() }) {
                Image(systemName: "arrow.triangle.2.circlepath")
            }
            .help(settings.localized("sync_document_tooltip"))
#endif

            Button(action: onEdit) {
                Image(systemName: "pencil")
            }
            Button(action: onDelete) {
                Image(systemName: "trash")
            }
            .buttonStyle(.borderless)
        }
        .font(.headline)
        .onAppear {
            let elapsed = Date().timeIntervalSince(AppLaunch.launchDate)
            let delay = max(0, 1 - elapsed)
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                updateProgress(to: progress)
            }
        }
        .onChange(of: progress) { newValue in
            updateProgress(to: newValue)
        }
        .onChange(of: stage.goal) { _ in
            updateProgress(to: progress)
        }
        .onChange(of: stage.entries.map(\.id)) { _ in
            updateProgress(to: progress)
        }
        .onChange(of: stage.entries.map(\.characterCount)) { _ in
            updateProgress(to: progress)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { note in
            if let id = note.object as? PersistentIdentifier, id == project.id {
                updateProgress(to: progress)
            }
        }
    }

#if os(macOS)
    private func selectSyncFile() {
        if stage.syncType != nil {
            let request = StageSyncInfoRequest(stageID: stage.id)
            openWindow(id: "stageSyncInfo", value: request)
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
                stage.syncType = .word
                stage.wordFilePath = url.path
                stage.wordFileBookmark = try? url.bookmarkData(options: .withSecurityScope)
                try? stage.modelContext?.save()
                DocumentSyncManager.startMonitoring(stage: stage)
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
        let request = StageScrivenerSelectRequest(stageID: stage.id, projectPath: projectURL.path)
        openWindow(id: "stageSelectScrivenerItem", value: request)
    }
#endif
}

#endif
