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

struct SharePreviewRequest: Codable, Hashable {
    var projectID: PersistentIdentifier
}

struct ScrivenerSelectRequest: Codable, Hashable {
    var projectID: PersistentIdentifier
    var projectPath: String
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
                .environment(\.locale, settings.locale)
#if os(macOS)
                .windowTitle(settings.localized("new_project"))
                .windowDefaultSize(width: layoutStep(35), height: layoutStep(20))
#endif
        }
        .modelContainer(DataController.shared)

        WindowGroup(id: "addStage", for: AddStageRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                AddStageView(project: project)
                    .environmentObject(settings)
                    .environment(\.locale, settings.locale)
#if os(macOS)
                    .windowTitle(settings.localized("new_stage"))
                    .windowDefaultSize(width: layoutStep(35), height: layoutStep(20))
#endif
            }
        }
        .modelContainer(DataController.shared)

        WindowGroup(id: "addEntry", for: AddEntryRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                if let stageID = request.stageID,
                   let stage = fetchStage(id: stageID, context: context) {
                    AddEntryView(project: project, stage: stage)
                        .environmentObject(settings)
                        .environment(\.locale, settings.locale)
#if os(macOS)
                        .windowTitle(settings.localized("new_entry"))
                        .windowDefaultSize(width: layoutStep(35), height: layoutStep(20))
#endif
                } else {
                    AddEntryView(project: project)
                        .environmentObject(settings)
                        .environment(\.locale, settings.locale)
#if os(macOS)
                        .windowTitle(settings.localized("new_entry"))
                        .windowDefaultSize(width: layoutStep(35), height: layoutStep(20))
#endif
                }
            }
        }
        .modelContainer(DataController.shared)

        WindowGroup(id: "editEntry", for: EditEntryRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context),
               let entry = fetchEntry(id: request.entryID, context: context) {
                EditEntryView(project: project, entry: entry)
                    .environmentObject(settings)
                    .environment(\.locale, settings.locale)
#if os(macOS)
                    .windowTitle("NFProgress")
                    .windowDefaultSize(width: layoutStep(40), height: layoutStep(25))
#endif
            }
        }
        .modelContainer(DataController.shared)

        WindowGroup(id: "sharePreview", for: SharePreviewRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                ProgressSharePreview(project: project)
                    .environmentObject(settings)
                    .environment(\.locale, settings.locale)
#if os(macOS)
                    .windowTitle(settings.localized("share"))
                    .windowDefaultSize(width: 560, height: 730)
#endif
            }
        }
        .modelContainer(DataController.shared)

        WindowGroup(id: "selectScrivenerItem", for: ScrivenerSelectRequest.self) { binding in
            let context = ModelContext(DataController.shared)
            if let request = binding.wrappedValue,
               let project = fetchProject(id: request.projectID, context: context) {
                let url = URL(fileURLWithPath: request.projectPath)
                ScrivenerItemSelectView(project: project, projectURL: url)
                    .environmentObject(settings)
                    .environment(\.locale, settings.locale)
            }
        }
        .modelContainer(DataController.shared)
    }
}
#endif
