import Foundation

/// Base spacing step used for layout metrics.
let baseLayoutStep: CGFloat = 8

/// Computes scaled layout values such as spacing and padding.
/// - Parameters:
///   - base: The base value in points.
///   - scaleFactor: Current text scale factor.
/// - Returns: Scaled result `base * scaleFactor`.
func calcLayoutValue(base: CGFloat) -> CGFloat {
    base
}

/// Returns layout value as a multiple of ``baseLayoutStep`` scaled by ``scaleFactor``.
func layoutStep(_ multiplier: CGFloat = 1) -> CGFloat {
    calcLayoutValue(base: baseLayoutStep * multiplier)
}

#if canImport(SwiftUI)
import SwiftUI

/// View modifier applying padding based on ``layoutStep``.
private struct ScaledPaddingModifier: ViewModifier {
    var multiplier: CGFloat
    var edges: Edge.Set

    func body(content: Content) -> some View {
        let value = layoutStep(multiplier)
        content.padding(edges, value)
    }
}

extension View {
    /// Adds padding using ``layoutStep``.
    func scaledPadding(_ multiplier: CGFloat = 1, _ edges: Edge.Set = .all) -> some View {
        modifier(ScaledPaddingModifier(multiplier: multiplier, edges: edges))
    }
}

/// Returns spacing value using ``layoutStep``.
func scaledSpacing(_ multiplier: CGFloat = 1) -> CGFloat {
    layoutStep(multiplier)
}
#endif
