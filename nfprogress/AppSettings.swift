import SwiftUI

@MainActor
final class AppSettings: ObservableObject {
    private let defaults = UserDefaults.standard

    @Published var disableLaunchAnimations: Bool {
        didSet { defaults.set(disableLaunchAnimations, forKey: "disableLaunchAnimations") }
    }

    @Published var disableAllAnimations: Bool {
        didSet { defaults.set(disableAllAnimations, forKey: "disableAllAnimations") }
    }

    @Published var textScale: Double {
        didSet { defaults.set(textScale, forKey: "textScale") }
    }

    init() {
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let value = defaults.double(forKey: "textScale")
        textScale = value == 0 ? 1.5 : value
    }
}

#if os(macOS)
func restartApp() {
    let url = URL(fileURLWithPath: Bundle.main.bundlePath)
    let task = Process()
    task.launchPath = "/usr/bin/open"
    task.arguments = [url.path]
    try? task.run()
    NSApplication.shared.terminate(nil)
}
#endif

private struct TextScaleKey: EnvironmentKey {
    static let defaultValue: Double = 1.5
}

extension EnvironmentValues {
    var textScale: Double {
        get { self[TextScaleKey.self] }
        set { self[TextScaleKey.self] = newValue }
    }
}

struct ApplyTextScale: ViewModifier {
    @Environment(\.textScale) private var textScale
    func body(content: Content) -> some View {
        content
            .environment(\.sizeCategory, category(for: textScale))
            .dynamicTypeSize(size(for: textScale))
            .scaleEffect(textScale)
    }

    private func size(for scale: Double) -> DynamicTypeSize {
        let sizes: [DynamicTypeSize] = [
            .xSmall, .small, .medium, .large, .xLarge, .xxLarge, .xxxLarge,
            .accessibility1, .accessibility2, .accessibility3, .accessibility4,
            .accessibility5
        ]

        let clamped = min(max(scale, 1), 3)
        let startIndex = 3 // `.large`
        let endIndex = sizes.count - 1
        let index = Int(round((clamped - 1) / 2 * Double(endIndex - startIndex))) + startIndex
        return sizes[index]
    }

    private func category(for scale: Double) -> ContentSizeCategory {
        let categories: [ContentSizeCategory] = [
            .extraSmall, .small, .medium, .large, .extraLarge,
            .extraExtraLarge, .extraExtraExtraLarge,
            .accessibilityMedium, .accessibilityLarge,
            .accessibilityExtraLarge, .accessibilityExtraExtraLarge,
            .accessibilityExtraExtraExtraLarge,
        ]

        let clamped = min(max(scale, 1), 3)
        let startIndex = 3 // `.large`
        let endIndex = categories.count - 1
        let index = Int(round((clamped - 1) / 2 * Double(endIndex - startIndex))) + startIndex
        return categories[index]
    }
}

extension View {
    func applyTextScale() -> some View {
        modifier(ApplyTextScale())
    }
}
