import SwiftUI

/// Defines color palettes used for progress animations.
enum ProgressPalette {
    case increase
    case decrease

    /// Starting color for the palette.
    var startColor: Color {
        switch self {
        case .increase: return .green
        case .decrease: return .orange
        }
    }

    /// Ending color for the palette.
    var endColor: Color {
        switch self {
        case .increase: return .orange
        case .decrease: return .green
        }
    }
}
