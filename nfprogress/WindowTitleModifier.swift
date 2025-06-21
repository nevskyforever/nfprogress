#if os(macOS)
import SwiftUI
import AppKit

private struct WindowAccessor: NSViewRepresentable {
    let title: String
    func makeNSView(context: Context) -> NSView {
        let nsView = NSView()
        DispatchQueue.main.async {
            if let window = nsView.window {
                window.title = title
                window.titleVisibility = .visible
            }
        }
        return nsView
    }
    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async {
            nsView.window?.title = title
            nsView.window?.titleVisibility = .visible
        }
    }
}

extension View {
    /// Sets the macOS window title for the view's window.
    func windowTitle(_ title: String) -> some View {
        self.background(WindowAccessor(title: title))
    }
}
#endif
