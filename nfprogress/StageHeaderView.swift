import SwiftUI
import SwiftData

/// Header view for displaying a stage with animated progress percentage
struct StageHeaderView: View {
    @Bindable var stage: Stage
    @Bindable var project: WritingProject
    var onEdit: () -> Void
    var onDelete: () -> Void

    /// Current progress value at the start of animation
    @State private var startProgress: Double = 0
    /// Target progress value
    @State private var endProgress: Double = 0

    /// Minimum and maximum allowed duration for the progress animation
    private let minDuration = 0.25
    private let maxDuration = 3.0

    /// Palette used for color interpolation
    @State private var palette: ProgressPalette = .increase

    /// Duration for the current animation
    @State private var duration: Double = 0.25

    /// Helper that maps progress to a color depending on palette
    private func color(for percent: Double) -> Color {
        switch palette {
        case .increase:
            return .interpolate(from: .green, to: .orange, fraction: percent)
        case .decrease:
            return .interpolate(from: .orange, to: .green, fraction: percent)
        }
    }

    /// Current progress percentage for this stage based on character count
    private var progress: Double {
        guard stage.goal > 0 else { return 0 }
        let percent = Double(stage.currentProgress) / Double(stage.goal)
        return min(max(percent, 0), 1.0)
    }

    /// Update the progress animation parameters
    private func updateProgress(to newValue: Double) {
        palette = newValue >= endProgress ? .increase : .decrease
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
                Text("Цель: \(stage.goal) знаков")
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
        .onChange(of: stage.entries.map(\.id)) { _ in
            updateProgress(to: progress)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: progress)
        }
    }
}
