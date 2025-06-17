import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    /// Цвет прогресса от красного к зеленому в зависимости от процента выполнения
    private var progressColor: Color {
        let clamped = max(0, min(1, project.progressPercentage))
        // От красного (0) к зеленому (0.33) по шкале hue
        let hue = clamped * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    var body: some View {
        ZStack {
            // Фоновый круг
            Circle()
                .stroke(Color.gray.opacity(0.3), lineWidth: 12)

            // Круг прогресса с динамическим цветом
            Circle()
                .trim(from: 0, to: CGFloat(project.progressPercentage))
                .stroke(progressColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))

            // Процент в центре
            Text("\(Int(project.progressPercentage * 100))%")
                .font(.system(size: 20))
                .bold()
        }
    }
}

