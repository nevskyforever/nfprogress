#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif
import UniformTypeIdentifiers
#if os(macOS)
import AppKit
#endif

struct ContentView: View {
  @Environment(\.modelContext) private var modelContext
  #if os(macOS)
  @Environment(\.openWindow) private var openWindow
  #endif
  @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]
  @State private var selectedProject: WritingProject?
  @State private var isExporting = false
  @State private var isImporting = false
  @State private var showingAddProject = false
  @State private var projectToDelete: WritingProject?
  @State private var showDeleteAlert = false

  @Environment(\.textScale) private var textScale
  private var circleHeight: CGFloat { layoutStep(10, scaleFactor: textScale) }

  private func projectRowLabel(for project: WritingProject) -> some View {
    VStack(alignment: .leading) {
      Text(project.title)
        .font(.headline)
        .applyTextScale()
        .frame(maxWidth: .infinity, alignment: .leading)
        .fixedSize(horizontal: false, vertical: true)
      HStack {
        Spacer()
        ProgressCircleView(project: project)
          .frame(height: circleHeight)
        Spacer()
      }
    }
    .padding(.vertical, scaledSpacing(1, scaleFactor: textScale))
    .frame(minHeight: circleHeight + layoutStep(2, scaleFactor: textScale))
    .background(Color.clear)
  }

  @ViewBuilder
  private func projectRow(for project: WritingProject) -> some View {
    if #available(iOS 16, macOS 13, *) {
      NavigationLink(value: project) {
        projectRowLabel(for: project)
      }
#if os(iOS)
      .buttonStyle(.plain)
#endif
      .listRowInsets(EdgeInsets())
    } else {
      NavigationLink(destination: ProjectDetailView(project: project)) {
        projectRowLabel(for: project)
      }
#if os(iOS)
      .buttonStyle(.plain)
#endif
      .listRowInsets(EdgeInsets())
      .simultaneousGesture(TapGesture().onEnded { selectedProject = project })
    }
  }

  private var sidebarView: some View {
    Group {
      if #available(iOS 16, macOS 13, *) {
        List(selection: $selectedProject) {
          ForEach(projects) { project in
              projectRow(for: project)
          }
          .onDelete(perform: deleteProjects)
          .onMove(perform: moveProjects)
        }
      } else {
        List {
          ForEach(projects) { project in
              projectRow(for: project)
          }
          .onDelete(perform: deleteProjects)
          .onMove(perform: moveProjects)
        }
      }
    }
    .listStyle(.plain)
    .applyCompatSplitWidth()
    .navigationTitle("my_texts")
    .toolbar {
        ToolbarItem {
          Button(action: addProject) {
            Label("add", systemImage: "plus")
          }
          .keyboardShortcut("N", modifiers: [.command, .shift])
        }
        ToolbarItem {
          Button(action: deleteSelectedProject) {
            Label("delete", systemImage: "minus")
          }
          .keyboardShortcut(.return, modifiers: .command)
          .disabled(selectedProject == nil)
        }
        #if os(macOS)
          ToolbarItemGroup(placement: .navigation) {
            if selectedProject != nil {
              Button("export") {
                exportSelectedProject()
              }
            }
            Button("import") {
              importSelectedProject()
            }
          }
        #else
          ToolbarItemGroup(placement: .navigationBarLeading) {
            if selectedProject != nil {
              Button("export") {
                exportSelectedProject()
              }
            }
            Button("import") {
              importSelectedProject()
            }
          }
        #endif
    }
  }

  @ViewBuilder
  private var detailView: some View {
      if let project = selectedProject {
        ProjectDetailView(project: project)
      } else {
        Text("select_project")
          .applyTextScale()
          .foregroundColor(.gray)
      }
  }

  @ViewBuilder
  private var splitView: some View {
    if #available(iOS 16, macOS 13, *) {
      NavigationSplitView(sidebar: {
        sidebarView
      }, detail: {
        detailView
      })
      .compatNavigationSplitViewColumnWidth(min: 200, ideal: 260, max: 400)
    } else {
      NavigationView {
        sidebarView
        detailView
      }
      .compatNavigationSplitViewColumnWidth(min: 200, ideal: 260, max: 400)
    }
  }

  var body: some View {
    splitView
      .compatNavigationDestination(for: WritingProject.self) { project in
        ProjectDetailView(project: project)
      }
      .fileExporter(
        isPresented: $isExporting,
        document: exportDocument,
        contentType: .commaSeparatedText,
      defaultFilename: exportFileName
    ) { result in
      if case .failure(let error) = result {
        print("Export failed: \(error.localizedDescription)")
      }
      isExporting = false
    }
    .fileImporter(
      isPresented: $isImporting,
      allowedContentTypes: [.commaSeparatedText]
    ) { result in
      switch result {
      case .success(let url):
        importCSV(from: url)
      case .failure(let error):
        print("Import failed: \(error.localizedDescription)")
      }
      isImporting = false
    }
    #if !os(macOS)
    .sheet(isPresented: $showingAddProject) {
      AddProjectView()
    }
    #endif
    .alert(isPresented: $showDeleteAlert) {
      Alert(
        title: Text(String(format: NSLocalizedString("delete_project_confirm", comment: ""), projectToDelete?.title ?? "")),
        message: Text("cannot_undo"),
        primaryButton: .destructive(Text("delete")) {
          if let project = projectToDelete {
            deleteProject(project)
          }
        },
        secondaryButton: .cancel()
      )
    }
    .onReceive(NotificationCenter.default.publisher(for: .menuAddProject)) { _ in
      addProject()
    }
    .onReceive(NotificationCenter.default.publisher(for: .menuImport)) { _ in
      importSelectedProject()
    }
    .onReceive(NotificationCenter.default.publisher(for: .menuExport)) { _ in
      exportSelectedProject()
    }
  }

  private func addProject() {
    #if os(macOS)
    openWindow(id: "addProject")
    #else
    showingAddProject = true
    #endif
  }

  private func deleteSelectedProject() {
    guard let project = selectedProject else { return }
    confirmDeleteProject(project)
  }

  private func deleteProjects(at offsets: IndexSet) {
    if let index = offsets.first {
      confirmDeleteProject(projects[index])
    }
  }

  private func confirmDeleteProject(_ project: WritingProject) {
    projectToDelete = project
    showDeleteAlert = true
  }

  private func deleteProject(_ project: WritingProject) {
    modelContext.delete(project)
    if selectedProject === project {
      selectedProject = nil
    }
    reorderProjects()
  }

#if os(macOS)
  // MARK: - Файловые операции macOS
  private func showSavePanel() {
    let panel = NSSavePanel()
    panel.allowedContentTypes = [.commaSeparatedText]
    panel.nameFieldStringValue = exportFileName
    if panel.runModal() == .OK, let url = panel.url {
      do {
        try exportDocument.text.write(to: url, atomically: true, encoding: .utf8)
      } catch {
        print("Export failed: \(error.localizedDescription)")
      }
    }
  }

  private func showOpenPanel() {
    let panel = NSOpenPanel()
    panel.allowedContentTypes = [.commaSeparatedText]
    panel.allowsMultipleSelection = false
    if panel.runModal() == .OK, let url = panel.url {
      importCSV(from: url)
    }
  }
#endif

  // MARK: - Экспорт
  private func exportSelectedProject() {
#if os(macOS)
    showSavePanel()
#else
    isExporting = true
#endif
  }

  private var exportDocument: CSVDocument {
    guard let project = selectedProject else {
      return CSVDocument(text: "")
    }
    let csv = CSVManager.csvString(for: project)
    return CSVDocument(text: csv)
  }

  private var exportFileName: String {
    guard let project = selectedProject else {
      return "Project.csv"
    }
    let base = project.title.replacingOccurrences(of: " ", with: "_")
    return base + ".csv"
  }

  // MARK: - Импорт
  private func importSelectedProject() {
#if os(macOS)
    showOpenPanel()
#else
    isImporting = true
#endif
  }


  private func importCSV(from url: URL) {
    guard let data = try? Data(contentsOf: url),
      let text = String(data: data, encoding: .utf8)
    else { return }
    let imported = CSVManager.importProjects(from: text)
    for project in imported {
      modelContext.insert(project)
    }
    try? modelContext.save()
    isImporting = false
  }

  private func moveProjects(from source: IndexSet, to destination: Int) {
    var ordered = projects
    ordered.move(fromOffsets: source, toOffset: destination)
    for (index, project) in ordered.enumerated() {
      project.order = index
    }
    try? modelContext.save()
  }

  private func reorderProjects() {
    for (index, project) in projects.enumerated() {
      project.order = index
    }
    try? modelContext.save()
  }
}
#endif
