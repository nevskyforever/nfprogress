#if os(macOS)
import SwiftUI
import AppKit

private struct WindowDefaultSizeSetter: NSViewRepresentable {
    var width: CGFloat
    var height: CGFloat

    class Coordinator {
        var applied = false
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { apply(to: view, coordinator: context.coordinator) }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async { apply(to: nsView, coordinator: context.coordinator) }
    }

    private func apply(to view: NSView, coordinator: Coordinator) {
        guard let window = view.window, !coordinator.applied else { return }
        coordinator.applied = true

        if !window.frameAutosaveName.isEmpty {
            let key = "NSWindow Frame \(window.frameAutosaveName)"
            if UserDefaults.standard.object(forKey: key) != nil {
                return
            }
        }

        var frame = window.frame
        frame.size = NSSize(width: width, height: height)
        window.setFrame(frame, display: true)
    }
}

extension View {
    /// Устанавливает размер окна macOS по умолчанию для данного представления.
    func windowDefaultSize(width: CGFloat, height: CGFloat) -> some View {
        background(WindowDefaultSizeSetter(width: width, height: height))
    }
}
#endif
