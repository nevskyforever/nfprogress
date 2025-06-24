#if canImport(SwiftUI)
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

/// Удобный инициализатор ``SwiftUI.Image`` из ``OSImage``.
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

