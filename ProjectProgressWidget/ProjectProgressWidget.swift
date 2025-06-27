#if canImport(WidgetKit) && canImport(SwiftUI)
import SwiftUI
import WidgetKit
import AppIntents
import nfprogress
#if canImport(SwiftData)
import SwiftData
#endif

@available(iOS 17, macOS 14, *)
struct SelectProjectIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Выберите проект"
    static var description = IntentDescription("Проект для отображения прогресса")

    @Parameter(title: "Проект")
    var project: ProjectEntity?
}

@available(iOS 17, macOS 14, *)
struct ProjectProgressEntry: TimelineEntry {
    let date: Date
    let projectID: PersistentIdentifier?
}

@available(iOS 17, macOS 14, *)
struct ProjectProgressProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> ProjectProgressEntry {
        ProjectProgressEntry(date: .now, projectID: nil)
    }

    func snapshot(for configuration: SelectProjectIntent, in context: Context) async -> ProjectProgressEntry {
        ProjectProgressEntry(date: .now, projectID: configuration.project?.id)
    }

    func timeline(for configuration: SelectProjectIntent, in context: Context) async -> Timeline<ProjectProgressEntry> {
        let entry = ProjectProgressEntry(date: .now, projectID: configuration.project?.id)
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(3600)))
    }
}

@available(iOS 17, macOS 14, *)
struct ProjectProgressWidgetEntryView: View {
    var entry: ProjectProgressProvider.Entry

    @Environment(\.modelContext) private var modelContext

    private var project: WritingProject? {
#if canImport(SwiftData)
        guard let id = entry.projectID else { return nil }
        let descriptor = FetchDescriptor<WritingProject>()
        if let projects = try? modelContext.fetch(descriptor) {
            return projects.first { $0.id == id }
        }
        return nil
#else
        nil
#endif
    }

    var body: some View {
        if let project {
            VStack(alignment: .center, spacing: 4) {
                Text(project.title)
                    .font(.headline)
                    .multilineTextAlignment(.center)
                ProgressView(value: project.progress)
                    .progressViewStyle(.circular)
                    .frame(width: 60, height: 60)
                if let deadline = project.deadline {
                    let days = Calendar.current.dateComponents([.day], from: .now, to: deadline).day ?? 0
                    if days > 0 {
                        Text("\(days) дн. до дедлайна")
                            .font(.caption)
                    }
                }
            }.padding()
        } else {
            Text("Проект не выбран")
        }
    }
}

@available(iOS 17, macOS 14, *)
struct ProjectProgressWidget: Widget {
    var body: some WidgetConfiguration {
        AppIntentConfiguration(intent: SelectProjectIntent.self, provider: ProjectProgressProvider()) { entry in
            ProjectProgressWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Прогресс проекта")
        .description("Отображает прогресс выбранного проекта и дни до дедлайна")
    }
}

@available(iOS 17, macOS 14, *)
struct ProjectProgressWidgets: WidgetBundle {
    var body: some Widget {
        ProjectProgressWidget()
    }
}
#endif
