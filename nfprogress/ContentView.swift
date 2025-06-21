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
  @EnvironmentObject private var settings: AppSettings
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

  private let circleHeight: CGFloat = layoutStep(10)

  private var splitView: some View {
    NavigationSplitView(sidebar: {
      List {
        ForEach(projects) { project in
          Button(action: { selectedProject = project }) {
            projectRow(for: project)
              .frame(maxWidth: .infinity, alignment: .leading)
              .padding(.vertical, scaledSpacing(1))
              .frame(minHeight: circleHeight + layoutStep(2))
              .contentShape(Rectangle())
          }
          .listRowInsets(EdgeInsets())
          .buttonStyle(.plain)
        }
        .onDelete(perform: deleteProjects)
        .onMove(perform: moveProjects)
      }
      .listStyle(.plain)
      .navigationTitle("my_texts")
      .toolbar {
        ToolbarItem {
          Picker("", selection: $settings.projectListStyle) {
            Image(systemName: "chart.pie").tag(AppSettings.ProjectListStyle.detailed)
            Image(systemName: "list.bullet").tag(AppSettings.ProjectListStyle.compact)
          }
          .pickerStyle(.segmented)
        }
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
    }, detail: {
      if let project = selectedProject {
        ProjectDetailView(project: project)
      } else {
        Text("select_project")
          .foregroundColor(.gray)
      }
    })
    .navigationDestination(for: WritingProject.self) { project in
      ProjectDetailView(project: project)
    }
  }

  @ViewBuilder
  private func projectRow(for project: WritingProject) -> some View {
    switch settings.projectListStyle {
    case .detailed:
      VStack(alignment: .leading) {
        Text(project.title)
          .font(.headline)
          .frame(maxWidth: .infinity, alignment: .leading)
          .fixedSize(horizontal: false, vertical: true)
        HStack {
          Spacer()
          ProgressCircleView(project: project)
            .frame(height: circleHeight)
          Spacer()
        }
      }
    case .compact:
      CompactProjectRow(project: project)
    }
  }

  var body: some View {
    splitView
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
        title: Text(settings.localized("delete_project_confirm", projectToDelete?.title ?? "")),
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
