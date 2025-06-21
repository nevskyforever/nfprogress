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

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
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

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
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

