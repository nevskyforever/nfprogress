import Foundation
#if canImport(SwiftUI)
import SwiftUI
#endif

#if canImport(SwiftUI)
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
            let q = TextScale.quantized(textScale)
            if q != textScale { textScale = q; return }
            defaults.set(textScale, forKey: "textScale")
        }
    }

    /// Коэффициент масштабирования декоративных размеров и шрифтов.
    var scaleFactor: Double {
        get { textScale }
        set { textScale = newValue }
    }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let value = defaults.double(forKey: "textScale")
        let scale = value == 0 ? 1.0 : value
        textScale = TextScale.quantized(scale)
    }
}
#else
@MainActor
final class AppSettings {
    private let defaults: UserDefaults

    var disableLaunchAnimations: Bool {
        didSet { defaults.set(disableLaunchAnimations, forKey: "disableLaunchAnimations") }
    }

    var disableAllAnimations: Bool {
        didSet { defaults.set(disableAllAnimations, forKey: "disableAllAnimations") }
    }

    var textScale: Double {
        didSet {
            let q = TextScale.quantized(textScale)
            if q != textScale { textScale = q; return }
            defaults.set(textScale, forKey: "textScale")
        }
    }

    /// Коэффициент масштабирования декоративных размеров и шрифтов.
    var scaleFactor: Double {
        get { textScale }
        set { textScale = newValue }
    }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let value = defaults.double(forKey: "textScale")
        let scale = value == 0 ? 1.0 : value
        textScale = TextScale.quantized(scale)
    }
}
#endif

#if os(macOS) && canImport(SwiftUI)
func restartApp() {
    let url = URL(fileURLWithPath: Bundle.main.bundlePath)
    let task = Process()
    task.launchPath = "/usr/bin/open"
    task.arguments = [url.path]
    try? task.run()
    NSApplication.shared.terminate(nil)
}
#endif

#if canImport(SwiftUI)
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
#endif
