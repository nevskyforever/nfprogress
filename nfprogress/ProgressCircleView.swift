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

    /// Minimum and maximum allowed duration for the progress animation
    private let minDuration = 0.4
    private let maxDuration = 2.5

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
            updateProgress(to: project.progress)
        }
        .onChange(of: project.progress) { newValue in
            updateProgress(to: newValue)
        }
        .onChange(of: project.entries.map(\.id)) { _ in
            updateProgress(to: project.progress)
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map(\.id)) { _ in
            updateProgress(to: project.progress)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: project.progress)
        }
    }
}

