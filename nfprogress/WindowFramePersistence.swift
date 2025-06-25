#if os(macOS)
import SwiftUI
import AppKit

private struct WindowFramePersistence: NSViewRepresentable {
    var id: String

    class Coordinator: NSObject, NSWindowDelegate {
        var applied = false
        let id: String
        init(id: String) { self.id = id }

        func windowDidEndLiveResize(_ notification: Notification) {
            saveFrame(from: notification.object)
        }
        func windowDidMove(_ notification: Notification) {
            saveFrame(from: notification.object)
        }
        func windowWillClose(_ notification: Notification) {
            saveFrame(from: notification.object)
        }
        private func saveFrame(from object: Any?) {
            guard let window = object as? NSWindow else { return }
            let frameString = NSStringFromRect(window.frame)
            UserDefaults.standard.set(frameString, forKey: "windowFrame." + id)
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator(id: id) }

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { apply(to: view, coordinator: context.coordinator) }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async { apply(to: nsView, coordinator: context.coordinator) }
    }

    private func apply(to view: NSView, coordinator: Coordinator) {
        guard let window = view.window else { return }
        guard !coordinator.applied else { return }
        coordinator.applied = true
        window.delegate = coordinator
        if let frameStr = UserDefaults.standard.string(forKey: "windowFrame." + id) {
            let frame = NSRectFromString(frameStr)
            window.setFrame(frame, display: true)
        }
    }
}

extension View {
    /// Сохраняет и восстанавливает положение и размер окна macOS.
    func persistentWindowFrame(id: String = "main") -> some View {
        background(WindowFramePersistence(id: id))
    }
}
#endif
