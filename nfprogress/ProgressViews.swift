#if canImport(SwiftUI)
import SwiftUI

#if canImport(Charts)
import Charts
#endif
#if canImport(SwiftData)
import SwiftData
#endif

/// Текстовое поле, плавно анимирующее изменение чисел.
struct AnimatedCounterText: Animatable, View {
    /// Текущее значение счётчика в процентах (0...1).
    var value: Double
    /// Токен, определяющий размер шрифта процента
    var token: FontToken = .progressValue

    var animatableData: Double {
        get { value }
        set { value = newValue }
    }

    var body: some View {
        let percent = Int(ceil(value * 100))
        Text("\(percent)%")
            .scaledFont(token)
            .monospacedDigit()
            .bold()
    }
}


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


enum ProgressCircleStyle {
    /// Стиль колец в списке проектов
    case regular
    /// Увеличенный стиль в деталях проекта
    case large
}

struct ProgressCircleView: View {
    var project: WritingProject
    var index: Int = 0
    /// Общее число проектов для адаптации задержки анимации
    var totalCount: Int = 1
    /// При значении `true` прогресс сохраняется через ``ProgressAnimationTracker``.
    /// Это нужно, чтобы запускать анимацию при возврате к списку проектов.
    var trackProgress: Bool = true
    /// Визуальный стиль круга прогресса
    var style: ProgressCircleStyle = .regular

    @AppStorage("disableLaunchAnimations") private var disableLaunchAnimations = false
    @AppStorage("disableAllAnimations") private var disableAllAnimations = false

    /// Толщина кольца в зависимости от ``ProgressCircleStyle``
    private var ringWidth: CGFloat {
        style == .large ? layoutStep(3) : layoutStep(2)
    }

    /// Токен шрифта в зависимости от стиля
    private var fontToken: FontToken {
        style == .large ? .progressValueLarge : .progressValue
    }

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
    /// Флаг, показывающий, что видимая часть сейчас на экране.
    @State private var isVisible = false
    /// Последнее известное значение прогресса
    @State private var lastProgress: Double?

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
                    .scaledFont(fontToken)
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
            AnimatedCounterText(value: endProgress, token: fontToken)
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
            isVisible = true
            let saved = trackProgress ? ProgressAnimationTracker.lastProgress(for: project) : lastProgress

            if disableLaunchAnimations || disableAllAnimations {
                startProgress = progress
                endProgress = progress
            } else if let saved {
                startProgress = saved
                endProgress = saved
                if abs(saved - progress) > 0.0001 {
                    DispatchQueue.main.async { updateProgress(to: progress) }
                }
            } else {
                let elapsed = Date().timeIntervalSince(AppLaunch.launchDate)
                // Чем больше проектов, тем более растягиваем начало анимации
                let step = 0.3 + Double(totalCount) * 0.02
                let delay = max(0, 1 - elapsed) + Double(index) * step
                DispatchQueue.main.asyncAfter(deadline: .now() + delay) { updateProgress(to: progress) }
            }

            lastProgress = progress
            if trackProgress {
                ProgressAnimationTracker.setProgress(progress, for: project)
            }
        }
        .onDisappear {
            isVisible = false
            if trackProgress {
                ProgressAnimationTracker.setProgress(progress, for: project)
            }
            lastProgress = progress
        }
        .onChange(of: progress) { newValue in
            if isVisible {
                updateProgress(to: newValue, animated: !disableAllAnimations)
            }
            if trackProgress && isVisible {
                ProgressAnimationTracker.setProgress(newValue, for: project)
            }
            lastProgress = newValue
        }
        .onChange(of: project.entries.map { $0.id }) { _ in
            if trackProgress && isVisible {
                ProgressAnimationTracker.setProgress(progress, for: project)
            }
            if isVisible {
                updateProgress(to: progress, animated: !disableAllAnimations)
            }
            lastProgress = progress
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map { $0.id }) { _ in
            if trackProgress && isVisible {
                ProgressAnimationTracker.setProgress(progress, for: project)
            }
            if isVisible {
                updateProgress(to: progress, animated: !disableAllAnimations)
            }
            lastProgress = progress
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { note in
            if let id = note.object as? PersistentIdentifier, id == project.id {
                if trackProgress && isVisible {
                    ProgressAnimationTracker.setProgress(progress, for: project)
                }
                if isVisible {
                    updateProgress(to: progress, animated: !disableAllAnimations)
                }
                lastProgress = progress
            }
        }
        // Название и дедлайн проекта не влияют на прогресс,
        // поэтому игнорируем их изменения
    }
}



struct ProgressChartView: View {
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject

    private let viewSpacing: CGFloat = scaledSpacing(1)
    private let chartHeight: CGFloat = layoutStep(25)
    /// Минимальное расстояние между подписями оси X
    private let minLabelSpacing: CGFloat = 80

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {

            if project.streak > 0 {
                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .foregroundColor(.green)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .foregroundColor(.green)
                }
            }

            if project.dailyProgress.count >= 2 {
#if canImport(Charts)
                GeometryReader { geo in
                    let labels = project.dailyAxisLabels
                    let data = Array(project.dailyProgress.enumerated())
                    let width = max(geo.size.width,
                                    CGFloat(labels.count) * minLabelSpacing)
                    ScrollView([.horizontal, .vertical]) {
                        Chart {
                            // Целевая линия
                            RuleMark(y: .value(settings.localized("progress_chart_goal"), project.goal))
                                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                                .foregroundStyle(.gray)
                                .annotation(position: .top, alignment: .leading) {
                                    Text(settings.localized("goal_characters", project.goal))
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                }

                            // Линия прогресса
                            ForEach(data, id: \.1.date) { index, item in
                                LineMark(
                                    x: .value(settings.localized("date_field"), index),
                                    y: .value(settings.localized("characters_field"), item.progress)
                                )
                                .interpolationMethod(.monotone)
                                .symbol(.circle)
                                .foregroundStyle(.blue)
                            }
                        }
                        .chartXScale(domain: 0...max(labels.count - 1, 0))
                        .chartScrollableAxes(.horizontal)
                        .chartXVisibleDomain(length: {
                            let visible = min(labels.count, 7)
                            return Double(max(visible - 1, 1))
                        }())
                        .chartXAxis {
                            AxisMarks(values: Array(labels.indices)) { value in
                                if let i = value.as(Int.self), i < labels.count {
                                    AxisGridLine()
                                    AxisTick()
                                    AxisValueLabel {
                                        Text(labels[i])
                                    }
                                }
                            }
                        }
                        .frame(width: width, alignment: .leading)
                    }
                    .frame(height: chartHeight, alignment: .top)
                }
                .frame(height: chartHeight)
                #else
                Text("charts_framework_required")
                    .frame(height: chartHeight, alignment: .top)
#endif
            }
        }
        .scaledPadding()
    }
}
#endif
