#if os(macOS)
import SwiftUI
import AppKit

private struct SidebarWidthPersistence: NSViewRepresentable {
    var key: String

    func makeCoordinator() -> Coordinator { Coordinator(key: key) }

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

    final class Coordinator {
        let key: String
        weak var view: NSView?
        var observation: NSObjectProtocol?

        init(key: String) { self.key = key }

        deinit {
            if let observation { NotificationCenter.default.removeObserver(observation) }
        }

        func setup() {
            guard let splitView = findSplitView() else { return }
            let defaults = UserDefaults.standard

            if observation == nil {
                if defaults.object(forKey: key) != nil {
                    let width = defaults.double(forKey: key)
                    splitView.setPosition(width, ofDividerAt: 0)
                }
                observation = NotificationCenter.default.addObserver(
                    forName: NSSplitView.didResizeSubviewsNotification,
                    object: splitView,
                    queue: .main
                ) { [weak self] _ in
                    self?.saveWidth()
                }
            }
            saveWidth()
        }

        private func findSplitView() -> NSSplitView? {
            var current = view
            while let c = current {
                if let split = c as? NSSplitView { return split }
                current = c.superview
            }
            return nil
        }

        private func saveWidth() {
            guard let splitView = findSplitView() else { return }
            let width = splitView.subviews.first?.frame.width ?? 0
            UserDefaults.standard.set(width, forKey: key)
        }
    }
}

extension View {
    /// Сохраняет и восстанавливает ширину боковой панели.
    func persistentSidebarWidth(key: String = "sidebarWidth") -> some View {
        background(SidebarWidthPersistence(key: key))
    }
}
#endif
