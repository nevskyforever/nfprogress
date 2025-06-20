import Foundation

/// Computes scaled layout values such as spacing and padding.
/// - Parameters:
///   - base: The base value in points.
///   - scaleFactor: Current text scale factor.
/// - Returns: Scaled result `base * scaleFactor`.
func calcLayoutValue(base: Double, scaleFactor: Double) -> Double {
    base * scaleFactor
}
