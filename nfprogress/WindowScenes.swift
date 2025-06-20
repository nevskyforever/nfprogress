#if os(macOS)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif

struct AddStageRequest: Codable, Hashable {
    var projectID: PersistentIdentifier
}

struct AddEntryRequest: Codable, Hashable {
    var projectID: PersistentIdentifier
    var stageID: UUID?
}

struct EditEntryRequest: Codable, Hashable {
    var projectID: PersistentIdentifier
    var entryID: UUID
}

private func fetchProject(id: PersistentIdentifier, context: ModelContext) -> WritingProject? {
    let descriptor = FetchDescriptor<WritingProject>(
        predicate: #Predicate { $0.id == id }
    )
    return try? context.fetch(descriptor).first
}

private func fetchStage(id: UUID, context: ModelContext) -> Stage? {
    let descriptor = FetchDescriptor<Stage>(
        predicate: #Predicate { $0.id == id }
    )
    return try? context.fetch(descriptor).first
}

private func fetchEntry(id: UUID, context: ModelContext) -> Entry? {
    let descriptor = FetchDescriptor<Entry>(
        predicate: #Predicate { $0.id == id }
    )
    return try? context.fetch(descriptor).first
}

extension nfprogressApp {
    @SceneBuilder
    var additionalWindows: some Scene {
        WindowGroup(id: "addProject") {
            AddProjectView()
                .environmentObject(settings)
        }
        .defaultSize(width: layoutStep(34), height: layoutStep(20))
        .modelContainer(DataController.shared)

        WindowGroup(id: "addStage", for: AddStageRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                AddStageView(project: project)
                    .environmentObject(settings)
            }
        }
        .defaultSize(width: layoutStep(34), height: layoutStep(20))
        .modelContainer(DataController.shared)

        WindowGroup(id: "addEntry", for: AddEntryRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                if let stageID = request.stageID,
                   let stage = fetchStage(id: stageID, context: context) {
                    AddEntryView(project: project, stage: stage)
                        .environmentObject(settings)
                } else {
                    AddEntryView(project: project)
                        .environmentObject(settings)
                }
            }
        }
        .defaultSize(width: layoutStep(34), height: layoutStep(20))
        .modelContainer(DataController.shared)

        WindowGroup(id: "editEntry", for: EditEntryRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context),
               let entry = fetchEntry(id: request.entryID, context: context) {
                EditEntryView(project: project, entry: entry)
                    .environmentObject(settings)
            }
        }
        .modelContainer(DataController.shared)
    }
}
#endif
