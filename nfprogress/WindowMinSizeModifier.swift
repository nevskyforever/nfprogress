#if os(macOS)
import SwiftUI
import AppKit

private struct WindowMinWidthSetter: NSViewRepresentable {
    var width: CGFloat

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { apply(to: view) }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async { apply(to: nsView) }
    }

    private func apply(to view: NSView) {
        guard let window = view.window else { return }
        var size = window.contentMinSize
        size.width = width
        window.contentMinSize = size
        if window.frame.width < width {
            var frame = window.frame
            frame.size.width = width
            window.setFrame(frame, display: true)
        }
    }
}

extension View {
    /// Устанавливает минимальную ширину окна macOS для данного представления.
    func windowMinWidth(_ width: CGFloat) -> some View {
        background(WindowMinWidthSetter(width: width))
    }
}
#endif
