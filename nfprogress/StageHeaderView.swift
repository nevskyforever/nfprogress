import SwiftUI

/// Header view for displaying a stage with animated progress percentage
struct StageHeaderView: View {
    @Bindable var stage: Stage
    var onEdit: () -> Void
    var onDelete: () -> Void

    /// Currently displayed progress value (0...1)
    @State private var displayedProgress: Double = 0

    /// Duration for animation to match progress circle
    private let animationDuration = 1.8

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
            displayedProgress = stage.progressPercentage
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            withAnimation(.easeOut(duration: animationDuration)) {
                displayedProgress = stage.progressPercentage
            }
        }
    }
}
