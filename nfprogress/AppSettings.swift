import Foundation
#if canImport(SwiftUI)
import SwiftUI
#endif

// Значения по умолчанию для предварительного просмотра экспорта.
// При наличии SwiftUI размер круга вычисляется из `shareImageSize`,
// чтобы диаграмма помещалась на холсте.
#if canImport(SwiftUI)
let defaultShareCircleSize: Double = Double(shareImageSize * 0.7)
#else
let defaultShareCircleSize: Double = 175
#endif
let defaultShareRingWidth: Double = 24
let defaultSharePercentSize: Double = 45
let defaultShareTitleSize: Double = 56
let defaultShareSpacing: Double = 16
let defaultShareTitleOffset: Double = 0


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

    enum ProjectListStyle: String, CaseIterable, Identifiable {
        case detailed
        case compact
        var id: String { rawValue }
    }

    enum ProjectSortOrder: String, CaseIterable, Identifiable {
        case title
        case progress
        var id: String { rawValue }

        var iconName: String {
            switch self {
            case .title: return "textformat"
            case .progress: return "chart.bar"
            }
        }

        var next: ProjectSortOrder { self == .title ? .progress : .title }
    }

    @Published var projectListStyle: ProjectListStyle {
        didSet { defaults.set(projectListStyle.rawValue, forKey: "projectListStyle") }
    }

    @Published var projectSortOrder: ProjectSortOrder {
        didSet { defaults.set(projectSortOrder.rawValue, forKey: "projectSortOrder") }
    }

    // Последние использованные параметры экспорта
    @Published var lastShareCircleSize: Double {
        didSet { defaults.set(lastShareCircleSize, forKey: "lastShareCircleSize") }
    }
    @Published var lastShareRingWidth: Double {
        didSet { defaults.set(lastShareRingWidth, forKey: "lastShareRingWidth") }
    }
    @Published var lastSharePercentSize: Double {
        didSet { defaults.set(lastSharePercentSize, forKey: "lastSharePercentSize") }
    }
    @Published var lastShareTitleSize: Double {
        didSet { defaults.set(lastShareTitleSize, forKey: "lastShareTitleSize") }
    }
    @Published var lastShareSpacing: Double {
        didSet { defaults.set(lastShareSpacing, forKey: "lastShareSpacing") }
    }
    @Published var lastShareTitleOffset: Double {
        didSet { defaults.set(lastShareTitleOffset, forKey: "lastShareTitleOffset") }
    }

    @Published var syncInterval: Double {
        didSet {
            defaults.set(syncInterval, forKey: "syncInterval")
            #if os(macOS)
            DocumentSyncManager.updateSyncInterval(to: syncInterval)
            #endif
        }
    }

    @Published var pauseAllSync: Bool {
        didSet {
            defaults.set(pauseAllSync, forKey: "pauseAllSync")
            #if os(macOS)
            DocumentSyncManager.setGlobalPause(pauseAllSync)
            #endif
        }
    }

    var locale: Locale { Locale(identifier: language.resolvedIdentifier) }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let raw = defaults.string(forKey: "language") ?? AppLanguage.system.rawValue
        language = AppLanguage(rawValue: raw) ?? .system
        let styleRaw = defaults.string(forKey: "projectListStyle") ?? ProjectListStyle.detailed.rawValue
        projectListStyle = ProjectListStyle(rawValue: styleRaw) ?? .detailed
        let sortRaw = defaults.string(forKey: "projectSortOrder") ?? ProjectSortOrder.title.rawValue
        projectSortOrder = ProjectSortOrder(rawValue: sortRaw) ?? .title
        let c = defaults.double(forKey: "lastShareCircleSize")
        lastShareCircleSize = c == 0 ? defaultShareCircleSize : c
        let r = defaults.double(forKey: "lastShareRingWidth")
        lastShareRingWidth = r == 0 ? defaultShareRingWidth : r
        let p = defaults.double(forKey: "lastSharePercentSize")
        lastSharePercentSize = p == 0 ? defaultSharePercentSize : p
        let t = defaults.double(forKey: "lastShareTitleSize")
        lastShareTitleSize = t == 0 ? defaultShareTitleSize : t
        let s = defaults.double(forKey: "lastShareSpacing")
        lastShareSpacing = s == 0 ? defaultShareSpacing : s
        let o = defaults.double(forKey: "lastShareTitleOffset")
        lastShareTitleOffset = o == 0 ? defaultShareTitleOffset : o
        let i = defaults.double(forKey: "syncInterval")
        syncInterval = i == 0 ? 2 : i
        pauseAllSync = defaults.bool(forKey: "pauseAllSync")
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

    enum ProjectListStyle: String {
        case detailed
        case compact
    }

    enum ProjectSortOrder: String {
        case title
        case progress

        var iconName: String {
            switch self {
            case .title: return "textformat"
            case .progress: return "chart.bar"
            }
        }

        var next: ProjectSortOrder { self == .title ? .progress : .title }
    }

    var projectListStyle: ProjectListStyle {
        didSet { defaults.set(projectListStyle.rawValue, forKey: "projectListStyle") }
    }

    var projectSortOrder: ProjectSortOrder {
        didSet { defaults.set(projectSortOrder.rawValue, forKey: "projectSortOrder") }
    }

    // Последние использованные параметры экспорта
    var lastShareCircleSize: Double {
        didSet { defaults.set(lastShareCircleSize, forKey: "lastShareCircleSize") }
    }
    var lastShareRingWidth: Double {
        didSet { defaults.set(lastShareRingWidth, forKey: "lastShareRingWidth") }
    }
    var lastSharePercentSize: Double {
        didSet { defaults.set(lastSharePercentSize, forKey: "lastSharePercentSize") }
    }
    var lastShareTitleSize: Double {
        didSet { defaults.set(lastShareTitleSize, forKey: "lastShareTitleSize") }
    }
    var lastShareSpacing: Double {
        didSet { defaults.set(lastShareSpacing, forKey: "lastShareSpacing") }
    }
    var lastShareTitleOffset: Double {
        didSet { defaults.set(lastShareTitleOffset, forKey: "lastShareTitleOffset") }
    }

    var syncInterval: Double {
        didSet {
            defaults.set(syncInterval, forKey: "syncInterval")
            #if os(macOS)
            DocumentSyncManager.updateSyncInterval(to: syncInterval)
            #endif
        }
    }

    var pauseAllSync: Bool {
        didSet {
            defaults.set(pauseAllSync, forKey: "pauseAllSync")
            #if os(macOS)
            DocumentSyncManager.setGlobalPause(pauseAllSync)
            #endif
        }
    }

    var locale: Locale { Locale(identifier: language.resolvedIdentifier) }

    init(userDefaults: UserDefaults = .standard) {
        defaults = userDefaults
        disableLaunchAnimations = defaults.bool(forKey: "disableLaunchAnimations")
        disableAllAnimations = defaults.bool(forKey: "disableAllAnimations")
        let raw = defaults.string(forKey: "language") ?? AppLanguage.system.rawValue
        language = AppLanguage(rawValue: raw) ?? .system
        let styleRaw = defaults.string(forKey: "projectListStyle") ?? ProjectListStyle.detailed.rawValue
        projectListStyle = ProjectListStyle(rawValue: styleRaw) ?? .detailed
        let sortRaw = defaults.string(forKey: "projectSortOrder") ?? ProjectSortOrder.title.rawValue
        projectSortOrder = ProjectSortOrder(rawValue: sortRaw) ?? .title
        let c = defaults.double(forKey: "lastShareCircleSize")
        lastShareCircleSize = c == 0 ? defaultShareCircleSize : c
        let r = defaults.double(forKey: "lastShareRingWidth")
        lastShareRingWidth = r == 0 ? defaultShareRingWidth : r
        let p = defaults.double(forKey: "lastSharePercentSize")
        lastSharePercentSize = p == 0 ? defaultSharePercentSize : p
        let t = defaults.double(forKey: "lastShareTitleSize")
        lastShareTitleSize = t == 0 ? defaultShareTitleSize : t
        let s = defaults.double(forKey: "lastShareSpacing")
        lastShareSpacing = s == 0 ? defaultShareSpacing : s
        let o = defaults.double(forKey: "lastShareTitleOffset")
        lastShareTitleOffset = o == 0 ? defaultShareTitleOffset : o
        let i = defaults.double(forKey: "syncInterval")
        syncInterval = i == 0 ? 2 : i
        pauseAllSync = defaults.bool(forKey: "pauseAllSync")
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


extension AppSettings {
    func localized(_ key: String, _ args: CVarArg...) -> String {
        let id = language.resolvedIdentifier
        if let path = Bundle.main.path(forResource: id, ofType: "lproj"),
           let bundle = Bundle(path: path) {
            let format = bundle.localizedString(forKey: key, value: nil, table: nil)
            return String(format: format, arguments: args)
        }
        let format = Bundle.main.localizedString(forKey: key, value: nil, table: nil)
        return String(format: format, arguments: args)
    }
}
