#if os(macOS)
import SwiftUI
import AppKit

@MainActor
func openWindow<V: View>(title: String, size: CGSize = CGSize(width: 360, height: 360), @ViewBuilder content: () -> V) {
    let window = NSWindow(
        contentRect: NSRect(origin: .zero, size: NSSize(width: size.width, height: size.height)),
        styleMask: [.titled, .closable, .miniaturizable, .resizable],
        backing: .buffered,
        defer: false
    )
    window.title = title
    window.isReleasedWhenClosed = false
    let root = content().environment(\.dismiss, DismissAction { [weak window] in window?.close() })
    window.contentView = NSHostingView(rootView: root)
    window.makeKeyAndOrderFront(nil)
}
#endif
