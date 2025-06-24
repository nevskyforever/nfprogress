#if canImport(SwiftUI)
import SwiftUI
#endif

/// Базовые размеры шрифтов, используемые в приложении.
enum FontToken: Double, CaseIterable {
    /// Размер текста внутри колец прогресса в основном меню
    case progressValue = 20
    /// Увеличенный размер текста для прогресса внутри проекта
    case progressValueLarge = 30
}

/// Возвращает базовый размер шрифта для указанного токена.
func calcFontSize(token: FontToken) -> Double {
    token.rawValue
}

#if canImport(SwiftUI)
/// Модификатор, применяющий масштабированный размер шрифта.
struct ScaledFont: ViewModifier {
    var token: FontToken

    func body(content: Content) -> some View {
        let size = CGFloat(calcFontSize(token: token))
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
