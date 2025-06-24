#if os(macOS)
import Foundation

struct ScrivenerItem { let id: String; let title: String }

enum ScrivenerParser {
    /// Возвращает список элементов проекта Scrivener по пути к папке проекта.
    /// Поддерживаются проекты как новой, так и старой версии (``project.scrivx`` и ``binder.scrivproj``).
    static func items(in projectURL: URL) -> [ScrivenerItem] {
        var xmlURL = projectURL.appendingPathComponent("project.scrivx")
        if !FileManager.default.fileExists(atPath: xmlURL.path) {
            xmlURL = projectURL.appendingPathComponent("binder.scrivproj")
        }
        guard FileManager.default.fileExists(atPath: xmlURL.path),
              let doc = try? XMLDocument(contentsOf: xmlURL) else { return [] }
        guard let nodes = try? doc.nodes(forXPath: "//BinderItem") as? [XMLElement] else { return [] }
        return nodes.compactMap { node in
            guard let id = node.attribute(forName: "ID")?.stringValue,
                  let title = node.elements(forName: "Title").first?.stringValue else { return nil }
            return ScrivenerItem(id: id, title: title)
        }
    }
}
#endif
