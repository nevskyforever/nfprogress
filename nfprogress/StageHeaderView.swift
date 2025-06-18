import SwiftUI
import SwiftData

/// Header view for displaying a stage with animated progress percentage
struct StageHeaderView: View {
    @Bindable var stage: Stage
    @Bindable var project: WritingProject
    var onEdit: () -> Void
    var onDelete: () -> Void

    /// Currently displayed progress value (0...1)
    @State private var displayedProgress: Double = 0

    /// Minimum and maximum allowed duration for the progress animation
    private let minDuration = 0.4
    private let maxDuration = 3.0

    /// Current progress percentage for this stage
    private var progress: Double {
        stage.progressPercentage
    }

    /// Update the displayed progress with an animated transition
    private func updateProgress(to newValue: Double) {
        // Рассчитываем относительный диапазон изменения от 0 до 1
        let diff = abs(newValue - displayedProgress)
        let range = max(diff, 0.01)
        let scaled = min(range, 1.0)

        // Чем больше изменение, тем дольше длится анимация
        let duration = min(minDuration + scaled * (maxDuration - minDuration),
                           maxDuration)

        withAnimation(.easeOut(duration: duration)) {
            displayedProgress = newValue
        }
    }

    /// Color representing current progress
    private var progressColor: Color {
        let clamped = max(0, min(1, displayedProgress))
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(stage.title)
                Text("Цель: \(stage.goal) знаков")
                    .font(.caption)
                    .foregroundColor(.gray)
            }

            Spacer()

            AnimatedCounterText(value: displayedProgress)
                .foregroundColor(progressColor)

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
        .onChange(of: stage.entries.map(\.id)) { _ in
            updateProgress(to: progress)
        }
    }
}
