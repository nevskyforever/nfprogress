import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    /// Progress value at the start of animation
    @State private var startProgress: Double = 0
    /// Target progress value
    @State private var endProgress: Double = 0

    /// Palette for color interpolation
    @State private var palette: ProgressPalette = .increase

    /// Duration for the current animation
    @State private var duration: Double = 0.25

    /// Map progress value to a color depending on palette
    private func color(for percent: Double) -> Color {
        switch palette {
        case .increase:
            return .interpolate(from: .green, to: .orange, fraction: percent)
        case .decrease:
            return .interpolate(from: .orange, to: .green, fraction: percent)
        }
    }

    /// Minimum and maximum allowed duration for the progress animation
    private let minDuration = 0.25
    private let maxDuration = 3.0

    /// Update animation parameters when progress changes
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
        ZStack {
            // Background circle
            Circle()
                .stroke(Color.gray.opacity(0.3), lineWidth: 12)

            if #available(macOS 12, *) {
                let startColor = color(for: startProgress)
                let endColor = color(for: endProgress)

                AnimatedProgressView(
                    startPercent: startProgress,
                    endPercent: endProgress,
                    startColor: startColor,
                    endColor: endColor,
                    duration: duration
                ) { value, color in
                    let progressCircle = Circle()
                        .trim(from: 0, to: CGFloat(value))
                        .stroke(color, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                        .rotationEffect(.degrees(-90))

                    progressCircle
                    Text("\(Int(value * 100))%")
                        .font(.system(size: 20))
                        .monospacedDigit()
                        .bold()
                        .foregroundColor(color)
                }
            } else {
                let color = color(for: endProgress)
                Circle()
                    .trim(from: 0, to: CGFloat(endProgress))
                    .stroke(color, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                AnimatedCounterText(value: endProgress)
            }
        }
        .onAppear {
            let elapsed = Date().timeIntervalSince(AppLaunch.launchDate)
            let delay = max(0, 1 - elapsed)
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                updateProgress(to: project.progress)
            }
        }
        .onChange(of: project.progress) { newValue in
            updateProgress(to: newValue)
        }
        .onChange(of: project.entries.map { $0.id }) { _ in
            updateProgress(to: project.progress)
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map { $0.id }) { _ in
            updateProgress(to: project.progress)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: project.progress)
        }
    }
}

