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

    /// Computed colors for the current animation state
    private var startColor: Color { color(for: startProgress) }
    private var endColor: Color { color(for: endProgress) }

    /// Background circle behind the animated progress
    private var backgroundCircle: some View {
        Circle()
            .stroke(Color.gray.opacity(0.3), lineWidth: 12)
    }

    /// Helper to draw a progress ring with the given value and color
    private func ring(value: Double, color: Color) -> some View {
        Circle()
            .trim(from: 0, to: CGFloat(value))
            .stroke(color, style: StrokeStyle(lineWidth: 12, lineCap: .round))
            .rotationEffect(.degrees(-90))
    }

    /// Animated ring for macOS 12+
    @available(macOS 12, *)
    private var animatedRing: some View {
        AnimatedProgressView(
            startPercent: startProgress,
            endPercent: endProgress,
            startColor: startColor,
            endColor: endColor,
            duration: duration
        ) { value, color in
            ring(value: value, color: color)
            Text("\(Int(value * 100))%")
                .font(.system(size: 20))
                .monospacedDigit()
                .bold()
                .foregroundColor(color)
        }
    }

    /// Static fallback ring on older systems
    private var staticRing: some View {
        let color = endColor
        return ZStack {
            ring(value: endProgress, color: color)
            AnimatedCounterText(value: endProgress)
                .foregroundColor(color)
        }
    }

    /// Choose the appropriate ring depending on OS version
    @ViewBuilder
    private var progressRing: some View {
        if #available(macOS 12, *) {
            animatedRing
        } else {
            staticRing
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
            backgroundCircle
            progressRing
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

