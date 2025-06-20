#if canImport(SwiftUI)
import SwiftUI

/// Текстовое поле, плавно анимирующее изменение чисел.
struct AnimatedCounterText: Animatable, View {
    /// Текущее значение счётчика в процентах (0...1).
    var value: Double

    var animatableData: Double {
        get { value }
        set { value = newValue }
    }

    var body: some View {
        let percent = Int(ceil(value * 100))
        Text("\(percent)%")
            .scaledFont(.progressValue)
            .monospacedDigit()
            .bold()
            .applyTextScale()
    }
}


import SwiftUI

@available(macOS 12, *)
struct AnimatedProgressView<Content: View>: View {
    var startPercent: Double
    var endPercent: Double
    var startColor: Color
    var endColor: Color
    var duration: Double
    var content: (Double, Color) -> Content

    @State private var startDate = Date()

    var body: some View {
        TimelineView(.animation) { context in
            let elapsed = context.date.timeIntervalSince(startDate)
            let fraction = min(1, max(0, elapsed / duration))
            let value = startPercent + (endPercent - startPercent) * fraction
            let color = Color.interpolate(from: startColor, to: endColor, fraction: fraction)
            content(value, color)
        }
        .onAppear { startDate = Date() }
        .onChange(of: startPercent) { _ in startDate = Date() }
        .onChange(of: endPercent) { _ in startDate = Date() }
        .onChange(of: startColor) { _ in startDate = Date() }
        .onChange(of: endColor) { _ in startDate = Date() }
        .onChange(of: duration) { _ in startDate = Date() }
    }
}


import SwiftUI

struct ProgressCircleView: View {
    var project: WritingProject

    @AppStorage("disableLaunchAnimations") private var disableLaunchAnimations = false
    @AppStorage("disableAllAnimations") private var disableAllAnimations = false
    @ScaledMetric private var baseRingWidth: CGFloat = 12
    @Environment(\.textScale) private var textScale
    private var ringWidth: CGFloat { baseRingWidth * textScale }

    /// Текущий процент выполнения проекта на основе общего количества символов
    private var progress: Double {
        guard project.goal > 0 else { return 0 }
        let percent = Double(project.currentProgress) / Double(project.goal)
        return min(max(percent, 0), 1.0)
    }

    /// Значение прогресса в начале анимации
    @State private var startProgress: Double = 0
    /// Целевое значение прогресса
    @State private var endProgress: Double = 0

    /// Длительность текущей анимации
    @State private var duration: Double = 0.25

    /// Преобразует значение прогресса в цвет от красного к зелёному
    private func color(for percent: Double) -> Color {
        .interpolate(from: .red, to: .green, fraction: percent)
    }

    /// Вычисленные цвета для текущего состояния анимации
    private var startColor: Color { color(for: startProgress) }
    private var endColor: Color { color(for: endProgress) }

    /// Фоновый круг за анимированным прогрессом
    private var backgroundCircle: some View {
        Circle()
            .stroke(Color.gray.opacity(0.3), lineWidth: ringWidth)
    }

    /// Рисует кольцо прогресса с указанным значением и цветом
    private func ring(value: Double, color: Color) -> some View {
        Circle()
            .trim(from: 0, to: CGFloat(value))
            .stroke(color, style: StrokeStyle(lineWidth: ringWidth, lineCap: .round))
            .rotationEffect(.degrees(-90))
    }

    /// Анимированное кольцо для macOS 12+
    @available(macOS 12, *)
    private var animatedRing: some View {
        AnimatedProgressView(
            startPercent: startProgress,
            endPercent: endProgress,
            startColor: startColor,
            endColor: endColor,
            duration: duration
        ) { value, color in
            ZStack {
                ring(value: value, color: color)
                let percent = Int(ceil(value * 100))
                Text("\(percent)%")
                    .scaledFont(.progressValue)
                    .monospacedDigit()
                    .bold()
                    .foregroundColor(color)
            }
        }
    }

    /// Статичное кольцо для старых систем
    private var staticRing: some View {
        let color = endColor
        return ZStack {
            ring(value: endProgress, color: color)
            AnimatedCounterText(value: endProgress)
                .foregroundColor(color)
        }
    }

    /// Выбор подходящего кольца в зависимости от версии ОС
    @ViewBuilder
    private var progressRing: some View {
        if disableAllAnimations {
            staticRing
        } else if #available(macOS 12, *) {
            animatedRing
        } else {
            staticRing
        }
    }

    /// Минимальная и максимальная длительность анимации прогресса
    private let minDuration = 0.25
    private let maxDuration = 3.0

    /// Обновить параметры анимации при изменении прогресса
    private func updateProgress(to newValue: Double, animated: Bool = true) {
        // Игнорируем лишние обновления, приводящие к нулевой длительности анимации
        guard abs(newValue - endProgress) > 0.0001 else { return }

        if animated {
            startProgress = endProgress
        } else {
            startProgress = newValue
        }
        endProgress = newValue

        if animated {
            let diff = abs(endProgress - startProgress)
            let range = max(diff, 0.01)
            let scaled = min(range, 1.0)
            duration = min(minDuration + scaled * (maxDuration - minDuration), maxDuration)
        } else {
            duration = 0
        }
    }

    var body: some View {
        ZStack {
            backgroundCircle
            progressRing
        }
        .onAppear {
            if disableLaunchAnimations || disableAllAnimations {
                startProgress = progress
                endProgress = progress
            } else {
                let elapsed = Date().timeIntervalSince(AppLaunch.launchDate)
                let delay = max(0, 1 - elapsed)
                DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                    updateProgress(to: progress)
                }
            }
        }
        .onChange(of: progress) { newValue in
            updateProgress(to: newValue, animated: !disableAllAnimations)
        }
        .onChange(of: project.entries.map { $0.id }) { _ in
            updateProgress(to: progress, animated: !disableAllAnimations)
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map { $0.id }) { _ in
            updateProgress(to: progress, animated: !disableAllAnimations)
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            updateProgress(to: progress, animated: !disableAllAnimations)
        }
    }
}



import SwiftUI
import Charts

struct ProgressChartView: View {
    var project: WritingProject

    @ScaledMetric private var baseSpacing: CGFloat = 8
    @Environment(\.textScale) private var textScale
    private var viewSpacing: CGFloat { baseSpacing * textScale }

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {

            if project.streak > 0 {
                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .applyTextScale()
                        .foregroundColor(.green)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .applyTextScale()
                        .foregroundColor(.green)
                }
            }

            if project.sortedEntries.count >= 2 {
                Chart {
                    // Целевая линия
                    RuleMark(y: .value("Цель", project.goal))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                        .foregroundStyle(.gray)
                        .annotation(position: .top, alignment: .leading) {
                            Text("Цель: \(project.goal)")
                                .font(.caption)
                                .applyTextScale()
                                .foregroundColor(.gray)
                        }

                    // Линия прогресса
                    ForEach(project.sortedEntries) { entry in
                        LineMark(
                            x: .value("Дата", entry.date),
                            y: .value("Символы", project.globalProgress(for: entry))
                        )
                        .interpolationMethod(.monotone)
                        .symbol(.circle)
                        .foregroundStyle(.blue)
                    }
                }
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        if let date = value.as(Date.self) {
                            AxisGridLine()
                            AxisTick()
                            AxisValueLabel {
                                Text(date.formatted(date: .numeric, time: .shortened))
                                    .applyTextScale()
                            }
                        }
                    }
                }
                .frame(height: 200)
            }
        }
        .padding(.top)
    }
}
#endif
