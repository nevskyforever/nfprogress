#if os(macOS)
import SwiftUI
import AppKit

private struct WindowMinWidthSetter: NSViewRepresentable {
    var width: CGFloat

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            if let window = view.window {
                var size = window.contentMinSize
                size.width = width
                window.contentMinSize = size
            }
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async {
            if let window = nsView.window {
                var size = window.contentMinSize
                size.width = width
                window.contentMinSize = size
            }
        }
    }
}

extension View {
    /// Sets the minimum width for the macOS window containing this view.
    func windowMinWidth(_ width: CGFloat) -> some View {
        background(WindowMinWidthSetter(width: width))
    }
}
#endif
