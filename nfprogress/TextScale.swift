import Foundation

public enum TextScaleLevel: Int, CaseIterable {
    case percent100 = 0
    case percent125
    case percent150
    case percent175
    case percent200
}

public struct TextScale {
    public static let values: [Double] = [1.0, 1.25, 1.5, 1.75, 2.0]

    /// Returns the nearest allowed scale value clamped to 1.0...2.0
    public static func quantized(_ value: Double) -> Double {
        let clamped = min(max(value, 1.0), 2.0)
        let step = 0.25
        let index = Int(round((clamped - 1.0) / step))
        let bounded = max(0, min(index, values.count - 1))
        return values[bounded]
    }

    /// Returns the discrete level for the provided scale
    public static func level(for value: Double) -> TextScaleLevel {
        let q = quantized(value)
        guard let idx = values.firstIndex(of: q) else { return .percent100 }
        return TextScaleLevel(rawValue: idx) ?? .percent100
    }
}
