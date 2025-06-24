#if os(macOS)
import Foundation

class ScrivenerItem: NSObject {
    let id: String
    let title: String
    let children: [ScrivenerItem]

    init(id: String, title: String, children: [ScrivenerItem] = []) {
        self.id = id
        self.title = title
        self.children = children
    }
}

enum ScrivenerParser {
    /// Возвращает структуру проекта Scrivener по пути к папке проекта.
    /// Поддерживаются проекты как новой, так и старой версии (``project.scrivx`` и ``binder.scrivproj``).
    static func items(in projectURL: URL) -> [ScrivenerItem] {
        var xmlURL = projectURL.appendingPathComponent("project.scrivx")
        if !FileManager.default.fileExists(atPath: xmlURL.path) {
            xmlURL = projectURL.appendingPathComponent("binder.scrivproj")
        }
        guard FileManager.default.fileExists(atPath: xmlURL.path),
              let doc = try? XMLDocument(contentsOf: xmlURL) else { return [] }
        // В разных версиях Scrivener корневой элемент отличается, поэтому
        // ищем первый узел <Binder> в документе целиком
        guard let binder = (try? doc.nodes(forXPath: "//Binder"))?.first as? XMLElement else { return [] }
        return binder.elements(forName: "BinderItem").compactMap { parseItem($0) }
    }

    private static func parseItem(_ element: XMLElement) -> ScrivenerItem? {
        guard let id = element.attribute(forName: "ID")?.stringValue,
              let title = element.elements(forName: "Title").first?.stringValue else { return nil }
        let childContainer = element.elements(forName: "Children").first
        let childElements = childContainer?.elements(forName: "BinderItem") ?? element.elements(forName: "BinderItem")
        let children = childElements.compactMap { parseItem($0) }
        return ScrivenerItem(id: id, title: title, children: children)
    }
}
#endif
