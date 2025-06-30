#if os(macOS)
import SwiftUI
import AppKit

struct ScrivenerItemSelectView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject
    let projectURL: URL
    private let items: [ScrivenerItem]
    @State private var selection: ScrivenerItem?

    init(project: WritingProject, projectURL: URL) {
        self.project = project
        self.projectURL = projectURL
        self.items = ScrivenerParser.items(in: projectURL)
    }

    private var defaultWidth: CGFloat {
        let frame = NSScreen.main?.visibleFrame ?? .init(x: 0, y: 0, width: 800, height: 600)
        return min(frame.width * 0.6, layoutStep(60))
    }

    private var defaultHeight: CGFloat {
        let frame = NSScreen.main?.visibleFrame ?? .init(x: 0, y: 0, width: 800, height: 600)
        return min(frame.height * 0.6, layoutStep(50))
    }

    var body: some View {
        VStack(spacing: scaledSpacing()) {
            Outline(items: items, selection: $selection)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            HStack {
                Spacer()
                Button(settings.localized("cancel")) { dismiss() }
                Button(settings.localized("done")) { confirm() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(minWidth: layoutStep(40), minHeight: layoutStep(30))
        .windowMinWidth(layoutStep(40))
        .windowDefaultSize(width: defaultWidth, height: defaultHeight)
        .windowTitle(settings.localized("scrivener_choose_item"))
    }

    private func confirm() {
        guard let item = selection else { return }
        if DocumentSyncManager.isScrivenerItemInUse(projectPath: projectURL.path, itemID: item.id) {
            let alert = NSAlert()
            alert.messageText = settings.localized("sync_already_linked")
            alert.runModal()
            return
        }
        project.syncType = .scrivener
        project.scrivenerProjectPath = projectURL.path
        project.scrivenerProjectBookmark = try? projectURL.bookmarkData(options: .withSecurityScope)
        project.scrivenerItemID = item.id
        project.scrivenerItemName = item.title
        try? project.modelContext?.save()
        DocumentSyncManager.startMonitoring(project: project)
        dismiss()
    }

    private struct Outline: NSViewRepresentable {
        var items: [ScrivenerItem]
        @Binding var selection: ScrivenerItem?

        func makeCoordinator() -> ScrivenerOutlineDataSource {
            ScrivenerOutlineDataSource(items: items) { item in
                selection = item
            }
        }

        func makeNSView(context: Context) -> NSScrollView {
            let outline = NSOutlineView()
            let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("title"))
            outline.addTableColumn(column)
            outline.outlineTableColumn = column
            outline.headerView = nil
            outline.dataSource = context.coordinator
            outline.delegate = context.coordinator
            outline.rowSizeStyle = .small
            outline.reloadData()
            outline.expandItem(nil, expandChildren: true)
            let scroll = NSScrollView()
            scroll.hasVerticalScroller = true
            scroll.documentView = outline
            return scroll
        }

        func updateNSView(_ nsView: NSScrollView, context: Context) {
            context.coordinator.items = items
            if let outline = nsView.documentView as? NSOutlineView {
                outline.reloadData()
                outline.expandItem(nil, expandChildren: true)
            }
        }
    }
}
#endif
