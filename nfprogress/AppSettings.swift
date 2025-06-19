import SwiftUI

enum AppSettings {
    private static let defaults = UserDefaults.standard

    static var disableLaunchAnimations: Bool {
        get { defaults.bool(forKey: "disableLaunchAnimations") }
        set { defaults.set(newValue, forKey: "disableLaunchAnimations") }
    }

    static var disableAllAnimations: Bool {
        get { defaults.bool(forKey: "disableAllAnimations") }
        set { defaults.set(newValue, forKey: "disableAllAnimations") }
    }

    static var textScale: Double {
        get {
            let value = defaults.double(forKey: "textScale")
            return value == 0 ? 1.0 : value
        }
        set {
            defaults.set(newValue, forKey: "textScale")
        }
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
    static let defaultValue: Double = 1.0
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
        content.dynamicTypeSize(size(for: textScale))
    }

    private func size(for scale: Double) -> DynamicTypeSize {
        let sizes: [DynamicTypeSize] = [
            .xSmall, .small, .medium, .large, .xLarge, .xxLarge, .xxxLarge,
            .accessibility1, .accessibility2, .accessibility3, .accessibility4,
            .accessibility5
        ]

        let clamped = min(max(scale, 1), 3)
        let index = Int(round((clamped - 1) / 2 * Double(sizes.count - 1)))
        return sizes[index]
    }
}

extension View {
    func applyTextScale() -> some View {
        modifier(ApplyTextScale())
    }
}
