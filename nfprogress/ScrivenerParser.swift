#if os(macOS)
import Foundation

struct ScrivenerItem { let id: String; let title: String }

enum ScrivenerParser {
    static func items(in projectURL: URL) -> [ScrivenerItem] {
        let xmlURL = projectURL.appendingPathComponent("project.scrivx")
        guard let doc = try? XMLDocument(contentsOf: xmlURL) else { return [] }
        guard let nodes = try? doc.nodes(forXPath: "//BinderItem") as? [XMLElement] else { return [] }
        return nodes.compactMap { node in
            guard let id = node.attribute(forName: "ID")?.stringValue,
                  let title = node.elements(forName: "Title").first?.stringValue else { return nil }
            return ScrivenerItem(id: id, title: title)
        }
    }
}
#endif
