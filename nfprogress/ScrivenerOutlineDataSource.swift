#if os(macOS)
import Cocoa

final class ScrivenerOutlineDataSource: NSObject, NSOutlineViewDataSource, NSOutlineViewDelegate {
    let items: [ScrivenerItem]

    init(items: [ScrivenerItem]) {
        self.items = items
    }

    func outlineView(_ outlineView: NSOutlineView, numberOfChildrenOfItem item: Any?) -> Int {
        let node = item as? ScrivenerItem
        return node?.children.count ?? items.count
    }

    func outlineView(_ outlineView: NSOutlineView, isItemExpandable item: Any) -> Bool {
        let node = item as! ScrivenerItem
        return !node.children.isEmpty
    }

    func outlineView(_ outlineView: NSOutlineView, child index: Int, ofItem item: Any?) -> Any {
        let node = item as? ScrivenerItem
        return node?.children[index] ?? items[index]
    }

    func outlineView(_ outlineView: NSOutlineView, viewFor tableColumn: NSTableColumn?, item: Any) -> NSView? {
        guard let node = item as? ScrivenerItem else { return nil }
        let identifier = NSUserInterfaceItemIdentifier("cell")
        let cell = outlineView.makeView(withIdentifier: identifier, owner: nil) as? NSTableCellView ?? NSTableCellView()
        cell.identifier = identifier
        if cell.textField == nil {
            let textField = NSTextField(labelWithString: node.title)
            textField.translatesAutoresizingMaskIntoConstraints = false
            cell.addSubview(textField)
            cell.textField = textField
            NSLayoutConstraint.activate([
                textField.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 2),
                textField.centerYAnchor.constraint(equalTo: cell.centerYAnchor)
            ])
        } else {
            cell.textField?.stringValue = node.title
        }
        return cell
    }
}
#endif
