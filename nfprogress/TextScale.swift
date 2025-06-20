import Foundation

public enum TextScaleLevel: Int, CaseIterable {
    case percent100 = 0
    case percent110
    case percent120
    case percent130
    case percent140
    case percent150
    /// Максимальное значение шкалы (159 %).
    case percent159
}

public struct TextScale {
    public static let values: [Double] = {
        var steps = stride(from: 1.0, through: 1.59, by: 0.10)
            .map { Double(round($0 * 100) / 100) }
        if let last = steps.last, last < 1.59 {
            steps.append(1.59)
        }
        return steps
    }()

    /// Returns the nearest allowed scale value clamped to 1.0...1.59
    public static func quantized(_ value: Double) -> Double {
        let clamped = min(max(value, 1.0), 1.59)
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
