#if canImport(SwiftUI)
import SwiftUI
#endif

/// Базовые размеры шрифтов, используемые в приложении.
enum FontToken: Double, CaseIterable {
    /// Размер текста внутри колец прогресса
    case progressValue = 20
}

/// Вычисляет итоговый размер шрифта с учетом масштабирования.
func calcFontSize(token: FontToken, scaleFactor: Double) -> Double {
    token.rawValue * scaleFactor
}

#if canImport(SwiftUI)
/// Модификатор, применяющий масштабированный размер шрифта.
struct ScaledFont: ViewModifier {
    @EnvironmentObject private var settings: AppSettings
    var token: FontToken

    func body(content: Content) -> some View {
        let size = CGFloat(calcFontSize(token: token, scaleFactor: settings.textScale))
        content.font(.system(size: size))
    }
}

extension View {
    /// Применяет масштабированный шрифт по токену.
    func scaledFont(_ token: FontToken) -> some View {
        modifier(ScaledFont(token: token))
    }
}
#endif
