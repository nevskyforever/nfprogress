import Foundation

/// Базовый шаг отступов, используемый в расчётах компоновки.
let baseLayoutStep: CGFloat = 8

/// Вычисляет масштабированные значения отступов и интервалов.
/// - Parameters:
///   - base: Базовое значение в точках.
///   - scaleFactor: Текущий коэффициент масштабирования текста.
/// - Returns: Результат `base * scaleFactor`.
func calcLayoutValue(base: CGFloat) -> CGFloat {
    base
}

/// Возвращает значение отступа как кратное ``baseLayoutStep`` с учётом ``scaleFactor``.
func layoutStep(_ multiplier: CGFloat = 1) -> CGFloat {
    calcLayoutValue(base: baseLayoutStep * multiplier)
}

#if canImport(SwiftUI)
import SwiftUI

/// Модификатор, добавляющий отступы с использованием ``layoutStep``.
private struct ScaledPaddingModifier: ViewModifier {
    var multiplier: CGFloat
    var edges: Edge.Set

    func body(content: Content) -> some View {
        let value = layoutStep(multiplier)
        content.padding(edges, value)
    }
}

extension View {
    /// Добавляет отступ, рассчитанный через ``layoutStep``.
    func scaledPadding(_ multiplier: CGFloat = 1, _ edges: Edge.Set = .all) -> some View {
        modifier(ScaledPaddingModifier(multiplier: multiplier, edges: edges))
    }
}

/// Returns spacing value using ``layoutStep``.
func scaledSpacing(_ multiplier: CGFloat = 1) -> CGFloat {
    layoutStep(multiplier)
}
#endif
