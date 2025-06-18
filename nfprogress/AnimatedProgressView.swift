import SwiftUI

@available(macOS 12, *)
struct AnimatedProgressView<Content: View>: View {
    var startPercent: Double
    var endPercent: Double
    var startColor: Color
    var endColor: Color
    var duration: Double
    var content: (Double, Color) -> Content

    @State private var startDate = Date()

    var body: some View {
        TimelineView(.animation) { context in
            let elapsed = context.date.timeIntervalSince(startDate)
            let fraction = min(1, max(0, elapsed / duration))
            let value = startPercent + (endPercent - startPercent) * fraction
            let color = Color.interpolate(from: startColor, to: endColor, fraction: fraction)
            content(value, color)
        }
        .onAppear { startDate = Date() }
        .onChange(of: startPercent) { _ in startDate = Date() }
        .onChange(of: endPercent) { _ in startDate = Date() }
        .onChange(of: startColor) { _ in startDate = Date() }
        .onChange(of: endColor) { _ in startDate = Date() }
        .onChange(of: duration) { _ in startDate = Date() }
    }
}
