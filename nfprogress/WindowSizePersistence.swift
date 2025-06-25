#if os(macOS)
import SwiftUI
import AppKit

private struct WindowSizePersistence: NSViewRepresentable {
    var id: String

    func makeCoordinator() -> Coordinator { Coordinator(id: id) }

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        context.coordinator.view = view
        DispatchQueue.main.async { context.coordinator.setup() }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        context.coordinator.view = nsView
        DispatchQueue.main.async { context.coordinator.setup() }
    }

    final class Coordinator: NSObject {
        let id: String
        weak var view: NSView?
        var observation: NSObjectProtocol?

        init(id: String) { self.id = id }

        deinit {
            if let observation { NotificationCenter.default.removeObserver(observation) }
        }

        func setup() {
            guard let window = view?.window else { return }
            let defaults = UserDefaults.standard
            let widthKey = "\(id)_width"
            let heightKey = "\(id)_height"

            if observation == nil {
                if defaults.object(forKey: widthKey) != nil,
                   defaults.object(forKey: heightKey) != nil {
                    var frame = window.frame
                    frame.size = NSSize(width: defaults.double(forKey: widthKey),
                                        height: defaults.double(forKey: heightKey))
                    window.setFrame(frame, display: true)
                }
                observation = NotificationCenter.default.addObserver(
                    forName: NSWindow.didEndLiveResizeNotification,
                    object: window,
                    queue: .main
                ) { [weak self] _ in
                    self?.saveSize()
                }
            }
            saveSize()
        }

        private func saveSize() {
            guard let window = view?.window else { return }
            let frame = window.frame
            let defaults = UserDefaults.standard
            defaults.set(frame.width, forKey: "\(id)_width")
            defaults.set(frame.height, forKey: "\(id)_height")
        }
    }
}

extension View {
    /// Сохраняет и восстанавливает размер окна macOS.
    func persistentWindowSize(id: String = "main") -> some View {
        background(WindowSizePersistence(id: id))
    }
}
#endif
