import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    /// Отображаемое значение прогресса, анимированное при появлении и изменении
    @State private var displayedProgress: Double = 0
    @State private var hasAppeared = false

    /// Цвет прогресса от красного к зеленому в зависимости от процента выполнения
    private var progressColor: Color {
        let clamped = max(0, min(1, displayedProgress))
        // От красного (0) к зеленому (0.33) по шкале hue
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    /// Общая продолжительность анимации
    private let animationDuration = 2.0

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

            // Процент в центре
            Text("\(Int(displayedProgress * 100))%")
                .font(.system(size: 20))
                .bold()
        }
        .onAppear {
            if !hasAppeared {
                hasAppeared = true
                displayedProgress = 0
                withAnimation(.easeOut(duration: animationDuration)) {
                    displayedProgress = project.progressPercentage
                }
            } else {
                displayedProgress = project.progressPercentage
            }
        }
        .onChange(of: project.progressPercentage) { newValue in
            withAnimation(.easeOut(duration: animationDuration)) {
                displayedProgress = newValue
            }
        }
    }
}

