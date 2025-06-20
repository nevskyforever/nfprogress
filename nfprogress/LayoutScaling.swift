import Foundation

/// Base spacing step used for layout metrics.
let baseLayoutStep: CGFloat = 8

/// Computes scaled layout values such as spacing and padding.
/// - Parameters:
///   - base: The base value in points.
///   - scaleFactor: Current text scale factor.
/// - Returns: Scaled result `base * scaleFactor`.
func calcLayoutValue(base: CGFloat, scaleFactor: Double) -> CGFloat {
    base * CGFloat(scaleFactor)
}

/// Returns layout value as a multiple of ``baseLayoutStep`` scaled by ``scaleFactor``.
func layoutStep(_ multiplier: CGFloat = 1, scaleFactor: Double) -> CGFloat {
    calcLayoutValue(base: baseLayoutStep * multiplier, scaleFactor: scaleFactor)
}

#if canImport(SwiftUI)
import SwiftUI

/// View modifier applying scaled padding based on ``textScale``.
private struct ScaledPaddingModifier: ViewModifier {
    @Environment(\.textScale) private var textScale
    var multiplier: CGFloat
    var edges: Edge.Set

    func body(content: Content) -> some View {
        let value = layoutStep(multiplier, scaleFactor: textScale)
        content.padding(edges, value)
    }
}

extension View {
    /// Adds padding scaled with ``textScale``.
    func scaledPadding(_ multiplier: CGFloat = 1, _ edges: Edge.Set = .all) -> some View {
        modifier(ScaledPaddingModifier(multiplier: multiplier, edges: edges))
    }
}

/// Returns spacing value scaled with ``textScale``.
func scaledSpacing(_ multiplier: CGFloat = 1, scaleFactor: Double) -> CGFloat {
    layoutStep(multiplier, scaleFactor: scaleFactor)
}
#endif
