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

    /// Base animation duration
    private let baseDuration = 0.4
    /// Extra time per percent of change
    private let scalingFactor = 0.03
    /// Minimum and maximum allowed duration
    private let minDuration = 0.4
    private let maxDuration = 2.5

    /// Current progress percentage for this stage
    private var progress: Double {
        stage.progressPercentage
    }

    /// Update the displayed progress with an animated transition
    private func updateProgress(to newValue: Double) {
        let diffPercent = abs(newValue - displayedProgress) * 100
        var duration = baseDuration + scalingFactor * diffPercent
        duration = min(max(duration, minDuration), maxDuration)
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
            updateProgress(to: progress)
        }
        .onChange(of: progress) { newValue in
            updateProgress(to: newValue)
        }
        .onChange(of: stage.entries.map(\.id)) { _ in
            updateProgress(to: progress)
        }
    }
}
