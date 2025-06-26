import Foundation
#if canImport(SwiftUI)
import SwiftUI
#if canImport(AppKit)
import AppKit
#elseif canImport(UIKit)
import UIKit
#endif
#endif

public struct HSB: Sendable { var h, s, b, a: Double }

#if canImport(SwiftUI)
extension Color {
    private func components() -> HSB {
#if canImport(AppKit)
        let c = NSColor(self).usingColorSpace(.deviceRGB) ?? NSColor(self)
        var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        c.getHue(&h, saturation: &s, brightness: &b, alpha: &a)
#elseif canImport(UIKit)
        var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        UIColor(self).getHue(&h, saturation: &s, brightness: &b, alpha: &a)
#else
        return .init(h: 0, s: 0, b: 0, a: 0)
#endif
        return .init(h: Double(h), s: Double(s), b: Double(b), a: Double(a))
    }

    var hsbComponents: HSB { components() }

    /// Интерполирует два цвета в пространстве HSB с циклическим изменением оттенка
    static func interpolate(from: Color, to: Color, fraction: Double) -> Color {
        let t = max(0, min(1, fraction))
        let f = from.components()
        let s = to.components()
        var delta = s.h - f.h
        if abs(delta) > 0.5 { delta += (delta > 0 ? -1 : 1) }
        let hue = f.h + delta * t
        let sat = f.s + (s.s - f.s) * t
        let bri = f.b + (s.b - f.b) * t
        let alpha = f.a + (s.a - f.a) * t
        return Color(hue: (hue < 0 ? hue + 1 : hue).truncatingRemainder(dividingBy: 1),
                     saturation: sat,
                     brightness: bri,
                     opacity: alpha)
    }
}
#else
public struct Color: Equatable, Sendable {
    public var hsbComponents: HSB { .init(h: hue, s: saturation, b: brightness, a: opacity) }

    public var hue: Double
    public var saturation: Double
    public var brightness: Double
    public var opacity: Double

    public init(hue: Double, saturation: Double, brightness: Double, opacity: Double = 1.0) {
        self.hue = hue
        self.saturation = saturation
        self.brightness = brightness
        self.opacity = opacity
    }

    public static let red = Color(hue: 0, saturation: 1, brightness: 1, opacity: 1)
    public static let blue = Color(hue: 2.0/3.0, saturation: 1, brightness: 1, opacity: 1)
    public static let green = Color(hue: 1.0/3.0, saturation: 1, brightness: 1, opacity: 1)

    /// Интерполирует два цвета в пространстве HSB с циклическим изменением оттенка
    public static func interpolate(from: Color, to: Color, fraction: Double) -> Color {
        let t = max(0, min(1, fraction))
        let f = from.hsbComponents
        let s = to.hsbComponents
        var delta = s.h - f.h
        if abs(delta) > 0.5 { delta += (delta > 0 ? -1 : 1) }
        let hue = f.h + delta * t
        let sat = f.s + (s.s - f.s) * t
        let bri = f.b + (s.b - f.b) * t
        let alpha = f.a + (s.a - f.a) * t
        return Color(hue: (hue < 0 ? hue + 1 : hue).truncatingRemainder(dividingBy: 1),
                     saturation: sat,
                     brightness: bri,
                     opacity: alpha)
    }
}
#endif
