#if canImport(SwiftUI)
import SwiftUI

extension TextScaleLevel {
    var dynamicTypeSize: DynamicTypeSize {
        switch self {
        case .percent100: return .large
        case .percent125: return .xLarge
        case .percent150: return .xxLarge
        case .percent175: return .xxxLarge
        case .percent200: return .accessibility1
        }
    }

    var contentSizeCategory: ContentSizeCategory {
        switch self {
        case .percent100: return .large
        case .percent125: return .extraLarge
        case .percent150: return .extraExtraLarge
        case .percent175: return .extraExtraExtraLarge
        case .percent200: return .accessibilityMedium
        }
    }
}
#endif
