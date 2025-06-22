#if canImport(SwiftUI)
import SwiftUI

/// Numeric text field that focuses automatically and selects its contents when it appears.
struct SelectAllIntField: View {
    /// Current text in the field. Should contain only digits.
    @Binding var text: String
    /// Localized title for accessibility.
    var placeholder: LocalizedStringKey
    /// Optional prompt displayed when the text is empty.
    var prompt: String? = nil
    /// Focuses the field when it appears.
    var focusOnAppear: Bool = false

    @State private var didFocus: Bool = false
    @FocusState private var isFocused: Bool

    var body: some View {
        TextField(placeholder,
                  text: $text,
                  prompt: prompt.map { Text(verbatim: $0) })
            .textFieldStyle(.roundedBorder)
#if os(iOS)
            .keyboardType(.numberPad)
#endif
            .focused($isFocused)
            .onAppear {
                guard focusOnAppear, !didFocus else { return }
                didFocus = true
                DispatchQueue.main.async {
                    isFocused = true
                }
            }
            .onChange(of: isFocused) { focused in
                if focused {
                    DispatchQueue.main.async { selectAll() }
                }
            }
    }

#if os(iOS)
    private func selectAll() {
        guard let controller = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .first?.windows.first(where: { $0.isKeyWindow }),
              let root = controller.rootViewController else { return }

        selectAll(from: root.view)
    }

    private func selectAll(from view: UIView) {
        if let textField = view as? UITextField, textField.isFirstResponder {
            textField.selectedTextRange = textField.textRange(from: textField.beginningOfDocument,
                                                             to: textField.endOfDocument)
        } else {
            for subview in view.subviews {
                selectAll(from: subview)
            }
        }
    }
#elseif os(macOS)
    private func selectAll() {
        if let editor = NSApp.keyWindow?.firstResponder as? NSTextView {
            editor.selectAll(nil)
        } else if let field = NSApp.keyWindow?.firstResponder as? NSTextField {
            field.currentEditor()?.selectAll(nil)
        }
    }
#else
    private func selectAll() {}
#endif
}
#endif
