#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

/// Animated percent text for project progress used in compact list view.
struct ProjectPercentView: View {
    var project: WritingProject

    @AppStorage("disableLaunchAnimations") private var disableLaunchAnimations = false
    @AppStorage("disableAllAnimations") private var disableAllAnimations = false

    private var progress: Double {
        guard project.goal > 0 else { return 0 }
        let percent = Double(project.currentProgress) / Double(project.goal)
        return min(max(percent, 0), 1.0)
    }

    @State private var startProgress: Double = 0
    @State private var endProgress: Double = 0
    @State private var duration: Double = 0.25
    /// Indicates that the view is currently visible.
    @State private var isVisible = false

    private let minDuration = 0.25
    private let maxDuration = 3.0

    private func color(for percent: Double) -> Color {
        .interpolate(from: .red, to: .green, fraction: percent)
    }

    private func updateProgress(to newValue: Double, animated: Bool = true) {
        guard abs(newValue - endProgress) > 0.0001 else { return }
        if animated { startProgress = endProgress } else { startProgress = newValue }
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

    @ViewBuilder
    private func progressText() -> some View {
        if disableAllAnimations {
            AnimatedCounterText(value: endProgress)
                .foregroundColor(color(for: endProgress))
        } else if #available(macOS 12, *) {
            AnimatedProgressView(
                startPercent: startProgress,
                endPercent: endProgress,
                startColor: color(for: startProgress),
                endColor: color(for: endProgress),
                duration: duration
            ) { value, color in
                let percent = Int(ceil(value * 100))
                return Text("\(percent)%")
                    .monospacedDigit()
                    .bold()
                    .foregroundColor(color)
            }
        } else {
            AnimatedCounterText(value: endProgress)
                .foregroundColor(color(for: endProgress))
        }
    }

    var body: some View {
        progressText()
            .scaledFont(.progressValue)
        .onAppear {
            isVisible = true
            let last = ProgressAnimationTracker.lastProgress(for: project)
            if disableLaunchAnimations || disableAllAnimations {
                startProgress = progress
                endProgress = progress
            } else if let last {
                startProgress = last
                endProgress = last
                if abs(last - progress) > 0.0001 {
                    DispatchQueue.main.async { updateProgress(to: progress) }
                }
            } else {
                let elapsed = Date().timeIntervalSince(AppLaunch.launchDate)
                let delay = max(0, 1 - elapsed)
                DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                    updateProgress(to: progress)
                }
            }
            ProgressAnimationTracker.setProgress(progress, for: project)
        }
        .onDisappear { isVisible = false }
        .onChange(of: progress) { newValue in
            if isVisible {
                ProgressAnimationTracker.setProgress(newValue, for: project)
                updateProgress(to: newValue, animated: !disableAllAnimations)
            }
        }
        .onChange(of: project.entries.map { $0.id }) { _ in
            if isVisible {
                ProgressAnimationTracker.setProgress(progress, for: project)
                updateProgress(to: progress, animated: !disableAllAnimations)
            }
        }
        .onChange(of: project.stages.flatMap { $0.entries }.map { $0.id }) { _ in
            if isVisible {
                ProgressAnimationTracker.setProgress(progress, for: project)
                updateProgress(to: progress, animated: !disableAllAnimations)
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .projectProgressChanged)) { _ in
            if isVisible {
                ProgressAnimationTracker.setProgress(progress, for: project)
                updateProgress(to: progress, animated: !disableAllAnimations)
            }
        }
    }
}

/// Row view showing only project title and progress percentage.
struct CompactProjectRow: View {
    var project: WritingProject
    var body: some View {
        HStack {
            Text(project.title)
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .fixedSize(horizontal: false, vertical: true)
            ProjectPercentView(project: project)
        }
        .padding(.vertical, scaledSpacing(1))
    }
}
#endif
