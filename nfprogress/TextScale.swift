import Foundation

public enum TextScaleLevel: Int, CaseIterable {
    case percent100 = 0
    case percent110
    case percent120
    case percent130
    case percent140
    case percent150
    case percent160
    case percent170
    case percent180
    case percent190
    case percent200
}

public struct TextScale {
    public static let values: [Double] = stride(from: 1.0, through: 2.0, by: 0.1).map { Double(round($0 * 10) / 10) }

    /// Returns the nearest allowed scale value clamped to 1.0...2.0
    public static func quantized(_ value: Double) -> Double {
        let clamped = min(max(value, 1.0), 2.0)
        let step = 0.1
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
