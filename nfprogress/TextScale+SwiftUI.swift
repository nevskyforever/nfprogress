#if canImport(SwiftUI)
import SwiftUI

extension TextScaleLevel {
    var dynamicTypeSize: DynamicTypeSize {
        switch self {
        case .percent100: return .large
        case .percent125: return .accessibility1
        case .percent150: return .accessibility2
        case .percent175: return .accessibility3
        case .percent200: return .accessibility4
        }
    }

    var contentSizeCategory: ContentSizeCategory {
        switch self {
        case .percent100: return .large
        case .percent125: return .accessibilityMedium
        case .percent150: return .accessibilityLarge
        case .percent175: return .accessibilityExtraLarge
        case .percent200: return .accessibilityExtraExtraLarge
        }
    }
}
#endif
