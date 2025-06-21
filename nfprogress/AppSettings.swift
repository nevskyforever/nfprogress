import Foundation
#if canImport(SwiftUI)
import SwiftUI
#endif

enum AppLanguage: String, CaseIterable, Identifiable {
    case system
    case en
    case ru

    var id: String { rawValue }

#if canImport(SwiftUI)
    var description: LocalizedStringKey {
        switch self {
        case .system: return "language_system"
        case .en: return "language_en"
        case .ru: return "language_ru"
        }
    }
#endif

    var resolvedIdentifier: String {
        switch self {
        case .system:
            let preferred = Locale.preferredLanguages.first ?? "en"
            let code = preferred.components(separatedBy: "-").first ?? "en"
            return Self.allCases.contains(where: { $0.rawValue == code }) ? code : "en"
        case .en:
            return "en"
        case .ru:
            return "ru"
        }
    }
}

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

    @Published var language: AppLanguage {
        didSet { defaults.set(language.rawValue, forKey: "language") }
    }

    var locale: Locale { Locale(identifier: language.resolvedIdentifier) }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let raw = defaults.string(forKey: "language") ?? AppLanguage.system.rawValue
        language = AppLanguage(rawValue: raw) ?? .system
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

    var language: AppLanguage {
        didSet { defaults.set(language.rawValue, forKey: "language") }
    }

    var locale: Locale { Locale(identifier: language.resolvedIdentifier) }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let raw = defaults.string(forKey: "language") ?? AppLanguage.system.rawValue
        language = AppLanguage(rawValue: raw) ?? .system
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

