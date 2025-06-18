import SwiftUI

/// Circular progress view with animated value and customizable overlay.
struct AnimatedProgressView<Content: View>: View {
    /// Target progress value (0...1)
    var value: Double
    var lineWidth: CGFloat = 12
    /// Overlay builder receiving the current animated value and color
    @ViewBuilder var content: (Double, Color) -> Content

    @State private var displayedProgress: Double = 0

    /// Base animation duration
    private let baseDuration = 0.4
    /// Extra time per percent of change
    private let scalingFactor = 0.03
    /// Minimum and maximum allowed duration
    private let minDuration = 0.4
    private let maxDuration = 2.5

    /// Current color based on displayed progress
    private var progressColor: Color {
        let clamped = max(0, min(1, displayedProgress))
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.gray.opacity(0.3), lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: CGFloat(displayedProgress))
                .stroke(progressColor, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
            content(displayedProgress, progressColor)
        }
        .onAppear { updateProgress(to: value) }
        .onChange(of: value) { newValue in updateProgress(to: newValue) }
    }

    /// Animate change of displayed progress
    private func updateProgress(to newValue: Double) {
        let diffPercent = abs(newValue - displayedProgress) * 100
        var duration = baseDuration + scalingFactor * diffPercent
        duration = min(max(duration, minDuration), maxDuration)
        withAnimation(.easeOut(duration: duration)) {
            displayedProgress = newValue
        }
    }
}
