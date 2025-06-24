#if canImport(SwiftUI)
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

/// Convenience initializer to create a ``SwiftUI.Image`` from ``OSImage``.
extension Image {
    init(osImage: OSImage) {
#if canImport(UIKit)
        self.init(uiImage: osImage)
#else
        self.init(nsImage: osImage)
#endif
    }
}
#endif

