import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    /// Отображаемое значение прогресса, анимированное только при изменении
    @State private var displayedProgress: Double = 0

    /// Цвет прогресса от красного к зеленому в зависимости от процента выполнения
    private var progressColor: Color {
        let clamped = max(0, min(1, displayedProgress))
        // От красного (0) к зеленому (0.33) по шкале hue
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    /// Base animation duration
    private let baseDuration = 0.4
    /// Extra time per percent of change
    private let scalingFactor = 0.03
    /// Minimum and maximum allowed duration
    private let minDuration = 0.4
    private let maxDuration = 2.5

    /// Update the displayed progress with an animated transition
    private func updateProgress(to newValue: Double) {
        let diffPercent = abs(newValue - displayedProgress) * 100
        var duration = baseDuration + scalingFactor * diffPercent
        duration = min(max(duration, minDuration), maxDuration)
        withAnimation(.easeOut(duration: duration)) {
            displayedProgress = newValue
        }
    }

    var body: some View {
        ZStack {
            // Фоновый круг
            Circle()
                .stroke(Color.gray.opacity(0.3), lineWidth: 12)

            // Круг прогресса с динамическим цветом
            Circle()
                .trim(from: 0, to: CGFloat(displayedProgress))
                .stroke(progressColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))

            // Процент в центре с плавной анимацией цифр
            AnimatedCounterText(value: displayedProgress)
        }
        .onAppear {
            updateProgress(to: project.progressPercentage)
        }
        .onChange(of: project.progressPercentage) { newValue in
            updateProgress(to: newValue)
        }
        .onChange(of: project.entries.map(\.id)) { _ in
            updateProgress(to: project.progressPercentage)
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map(\.id)) { _ in
            updateProgress(to: project.progressPercentage)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: project.progressPercentage)
        }
    }
}

