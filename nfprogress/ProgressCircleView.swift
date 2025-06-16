import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    var body: some View {
        ZStack {
            // Фоновый круг
            Circle()
                .stroke(Color.gray.opacity(0.3), lineWidth: 12)

            // Круг прогресса
            Circle()
                .trim(from: 0, to: CGFloat(project.progressPercentage))
                .stroke(Color.blue, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))

            // Процент в центре
            Text("\(Int(project.progressPercentage * 100))%")
                .font(.caption)
                .bold()
        }
    }
}

