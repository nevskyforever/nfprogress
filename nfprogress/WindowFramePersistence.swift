#if os(macOS)
import SwiftUI
import AppKit

private struct WindowFramePersistence: NSViewRepresentable {
    var id: String

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
        window.setFrameUsingName(id)
        window.setFrameAutosaveName(id)
    }
}

extension View {
    /// Сохраняет и восстанавливает положение и размер окна macOS.
    func persistentWindowFrame(id: String = "main") -> some View {
        background(WindowFramePersistence(id: id))
    }
}
#endif
