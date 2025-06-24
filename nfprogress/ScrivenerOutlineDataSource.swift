#if os(macOS)
import Cocoa

final class ScrivenerOutlineDataSource: NSObject, NSOutlineViewDataSource, NSOutlineViewDelegate {
    var items: [ScrivenerItem]
    var selectionHandler: ((ScrivenerItem) -> Void)?

    init(items: [ScrivenerItem], selectionHandler: ((ScrivenerItem) -> Void)? = nil) {
        self.items = items
        self.selectionHandler = selectionHandler
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

    func outlineViewSelectionDidChange(_ notification: Notification) {
        guard let outline = notification.object as? NSOutlineView else { return }
        let row = outline.selectedRow
        if row >= 0, let item = outline.item(atRow: row) as? ScrivenerItem {
            selectionHandler?(item)
        }
    }
}
#endif
