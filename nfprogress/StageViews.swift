import SwiftUI
import SwiftData

struct AddStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var project: WritingProject

    @State private var title = ""
    @State private var goal = 1000

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

            Text("new_stage")
                .font(.title2.bold())
                .applyTextScale()
            if project.stages.isEmpty && !project.entries.isEmpty {
                Text("all_entries_move")
                    .applyTextScale()
                    .multilineTextAlignment(.center)
                    .font(.caption)
                    .foregroundColor(.orange)
            }
            TextField("project_name", text: $title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            TextField("project_goal", value: $goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)
            Spacer()
            Button("create") { addStage() }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .padding(.bottom)
        }
        .padding()
        .frame(width: 320)
    }

    private func addStage() {
        let name = title.isEmpty ? String(localized: "stage_placeholder") : title
        let start = (project.stages.isEmpty && !project.entries.isEmpty) ? 0 : project.currentProgress
        let stage = Stage(title: name, goal: goal, startProgress: start)
        if project.stages.isEmpty && !project.entries.isEmpty {
            stage.entries = project.entries
            project.entries.removeAll()
        }
        project.stages.append(stage)
        NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        dismiss()
    }
}



import SwiftUI
import SwiftData

struct EditStageView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var stage: Stage

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

            Text("edit_stage")
                .font(.title2.bold())
                .applyTextScale()

            TextField("project_name", text: $stage.title)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            TextField("project_goal", value: $stage.goal, format: .number)
                .textFieldStyle(.roundedBorder)
                .frame(width: 200)

            Spacer()

            Button("done") {
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
        .onChange(of: stage.goal) { _ in
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }
}


import SwiftUI
import SwiftData

/// Заголовок этапа с анимированным отображением процента прогресса
struct StageHeaderView: View {
    @Bindable var stage: Stage
    @Bindable var project: WritingProject
    var onEdit: () -> Void
    var onDelete: () -> Void

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
                    .applyTextScale()
                Text("Цель: \(stage.goal) знаков")
                    .applyTextScale()
                    .font(.caption)
                    .foregroundColor(.gray)
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
                AnimatedCounterText(value: endProgress)
                    .foregroundColor(color(for: endProgress))
            }

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
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: progress)
        }
    }
}
