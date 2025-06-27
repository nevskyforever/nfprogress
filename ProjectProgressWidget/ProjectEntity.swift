import Foundation
#if canImport(AppIntents)
import AppIntents
#if canImport(SwiftData)
import SwiftData
#endif
#endif

#if canImport(AppIntents)
@available(iOS 17, macOS 14, *)
struct ProjectEntity: AppEntity {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Project")

    var title: String

    static var defaultQuery = ProjectQuery()

    init(id: PersistentIdentifier) {
#if canImport(SwiftData)
        if let project = try? DataController.mainContext.fetch(FetchDescriptor<WritingProject>()).first(where: { $0.id == id }) {
            title = project.title
        } else {
            title = ""
        }
#else
        title = ""
#endif
    }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: LocalizedStringResource(stringLiteral: title))
    }
}

@available(iOS 17, macOS 14, *)
struct ProjectQuery: EntityQuery {
    func entities(for identifiers: [PersistentIdentifier]) async throws -> [ProjectEntity] {
        identifiers.compactMap { ProjectEntity(id: $0) }
    }

    func suggestedEntities() async throws -> [ProjectEntity] {
#if canImport(SwiftData)
        let context = DataController.mainContext
        let projects = try context.fetch(FetchDescriptor<WritingProject>())
        return projects.map { ProjectEntity(id: $0.id) }
#else
        return []
#endif
    }
}
#endif
