import SwiftUI

@MainActor
final class AppSettings: ObservableObject {
    private let defaults: UserDefaults

    @Published var disableLaunchAnimations: Bool {
        didSet { defaults.set(disableLaunchAnimations, forKey: "disableLaunchAnimations") }
    }

    @Published var disableAllAnimations: Bool {
        didSet { defaults.set(disableAllAnimations, forKey: "disableAllAnimations") }
    }

    @Published var textScale: Double {
        didSet {
            let quantized = TextScale.quantized(textScale)
            if quantized != textScale { textScale = quantized; return }
            defaults.set(textScale, forKey: "textScale")
        }
    }

    init(userDefaults: UserDefaults = .standard) {
        self.defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let value = defaults.double(forKey: "textScale")
        let scale = value == 0 ? 1.0 : value
        textScale = TextScale.quantized(scale)
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
        let level = TextScale.level(for: textScale)
        return content
            .environment(\.sizeCategory, level.contentSizeCategory)
            .dynamicTypeSize(level.dynamicTypeSize)
    }
}

extension View {
    func applyTextScale() -> some View {
        modifier(ApplyTextScale())
    }
}

