#if canImport(SwiftUI)
import SwiftUI

extension TextScaleLevel {
    var dynamicTypeSize: DynamicTypeSize {
        switch self {
        case .percent100: return .large
        case .percent110: return .xLarge
        case .percent120: return .xxLarge
        case .percent130: return .xxxLarge
        case .percent140: return .accessibility1
        case .percent150: return .accessibility2
        case .percent159: return .accessibility3
        }
    }

    var contentSizeCategory: ContentSizeCategory {
        switch self {
        case .percent100: return .large
        case .percent110: return .extraLarge
        case .percent120: return .extraExtraLarge
        case .percent130: return .extraExtraExtraLarge
        case .percent140: return .accessibilityMedium
        case .percent150: return .accessibilityLarge
        case .percent159: return .accessibilityExtraLarge
        }
    }
}
#endif
