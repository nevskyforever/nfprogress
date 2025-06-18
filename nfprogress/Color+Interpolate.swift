import SwiftUI
#if canImport(AppKit)
import AppKit
#elseif canImport(UIKit)
import UIKit
#endif

extension Color {
    /// Interpolates between two colors using HSB space with cyclic hue.
    static func interpolate(from: Color, to: Color, fraction: Double) -> Color {
        let t = max(0, min(1, fraction))
        #if canImport(AppKit)
        let f = NSColor(from).usingColorSpace(.deviceRGB) ?? NSColor(from)
        let s = NSColor(to).usingColorSpace(.deviceRGB) ?? NSColor(to)
        var fh: CGFloat = 0, fs: CGFloat = 0, fb: CGFloat = 0, fa: CGFloat = 0
        var th: CGFloat = 0, ts: CGFloat = 0, tb: CGFloat = 0, ta: CGFloat = 0
        f.getHue(&fh, saturation: &fs, brightness: &fb, alpha: &fa)
        s.getHue(&th, saturation: &ts, brightness: &tb, alpha: &ta)
        #elseif canImport(UIKit)
        var fh: CGFloat = 0, fs: CGFloat = 0, fb: CGFloat = 0, fa: CGFloat = 0
        var th: CGFloat = 0, ts: CGFloat = 0, tb: CGFloat = 0, ta: CGFloat = 0
        UIColor(from).getHue(&fh, saturation: &fs, brightness: &fb, alpha: &fa)
        UIColor(to).getHue(&th, saturation: &ts, brightness: &tb, alpha: &ta)
        #endif
        // Shortest path hue interpolation with wraparound
        var delta = th - fh
        if abs(delta) > 0.5 { delta += (delta > 0 ? -1 : 1) }
        let hue = fh + delta * t
        let sat = fs + (ts - fs) * t
        let bri = fb + (tb - fb) * t
        let alpha = fa + (ta - fa) * t
        return Color(hue: Double((hue < 0 ? hue + 1 : hue).truncatingRemainder(dividingBy: 1)),
                     saturation: Double(sat),
                     brightness: Double(bri),
                     opacity: Double(alpha))
    }
}
