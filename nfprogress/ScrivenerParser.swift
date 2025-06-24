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
    /// Возвращает структуру проекта Scrivener по пути к пакету проекта.
    /// Поддерживаются проекты разных версий:
    ///  - стандартный файл `project.scrivx`
    ///  - файл с именем проекта и расширением `.scrivx`
    ///  - устаревший `binder.scrivproj`
    static func items(in projectURL: URL) -> [ScrivenerItem] {
        var xmlURL = projectURL.appendingPathComponent("project.scrivx")
        let fm = FileManager.default
        if !fm.fileExists(atPath: xmlURL.path) {
            if let name = try? fm.contentsOfDirectory(atPath: projectURL.path)
                .first(where: { $0.hasSuffix(".scrivx") }) {
                xmlURL = projectURL.appendingPathComponent(name)
            } else {
                xmlURL = projectURL.appendingPathComponent("binder.scrivproj")
            }
        }
        guard fm.fileExists(atPath: xmlURL.path),
              let data = try? Data(contentsOf: xmlURL),
              let doc = try? XMLDocument(data: data) else { return [] }

        // В разных версиях Scrivener корневой элемент отличается, поэтому
        // ищем первый подходящий узел
        let binder = (try? doc.nodes(forXPath: "//Binder"))?.first as? XMLElement ??
                     (try? doc.nodes(forXPath: "//root"))?.first as? XMLElement
        guard let binderNode = binder else { return [] }
        return binderNode.elements(forName: "BinderItem").compactMap { parseItem($0) }
    }

    private static func parseItem(_ element: XMLElement) -> ScrivenerItem? {
        let id = element.attribute(forName: "ID")?.stringValue ??
                 element.attribute(forName: "Uuid")?.stringValue ??
                 element.attribute(forName: "UUID")?.stringValue ??
                 element.attribute(forName: "uuid")?.stringValue
        guard let id, let title = element.elements(forName: "Title").first?.stringValue else { return nil }
        let childContainer = element.elements(forName: "Children").first ??
                              element.elements(forName: "SubDocuments").first
        let childElements = childContainer?.elements(forName: "BinderItem") ??
                            element.elements(forName: "BinderItem")
        let children = childElements.compactMap { parseItem($0) }
        return ScrivenerItem(id: id, title: title, children: children)
    }
}
#endif
