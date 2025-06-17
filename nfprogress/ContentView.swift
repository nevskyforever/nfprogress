import SwiftData
import SwiftUI
import UniformTypeIdentifiers
#if os(macOS)
import AppKit
#endif

struct ContentView: View {
  @Environment(\.modelContext) private var modelContext
  // Using an explicit comparison improves reliability of query updates
  @Query(filter: #Predicate<WritingProject> { $0.isArchived == false })
  private var projects: [WritingProject]
  @State private var selectedProject: WritingProject?
  @State private var isExporting = false
  @State private var isImporting = false
  @State private var showingAddProject = false
  @State private var projectToArchive: WritingProject?
  @State private var showArchiveAlert = false
  @State private var showArchivedList = false

  var body: some View {
    NavigationSplitView {
      List(selection: $selectedProject) {
        ForEach(projects, id: \.id) { project in
          NavigationLink(value: project) {
            VStack(alignment: .leading) {
              Text(project.title)
                .font(.headline)
              ProgressCircleView(project: project)
                .frame(height: 80)
            }
            .padding(.vertical, 4)
          }
          .swipeActions(edge: .trailing) {
            Button(role: .destructive) {
              confirmArchiveProject(project)
            } label: {
              Label("Архивировать", systemImage: "archivebox.fill")
            }
          }
        }
      }
      .navigationTitle("Мои тексты")
      .toolbar {
        ToolbarItem {
          Button(action: addProject) {
            Label("Добавить", systemImage: "plus")
          }
          .keyboardShortcut("N", modifiers: [.command, .shift])
        }
        ToolbarItem {
          Button(action: deleteSelectedProject) {
            Label("Архивировать", systemImage: "archivebox.fill")
          }
          .keyboardShortcut(.return, modifiers: .command)
          .disabled(selectedProject == nil)
        }
        ToolbarItem {
          Button {
            showArchivedList = true
          } label: {
            Label("Архив", systemImage: "archivebox")
          }
        }
        #if os(macOS)
          ToolbarItemGroup(placement: .navigation) {
            Button("Экспортировать") {
              exportSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Импортировать") {
              importSelectedProject()
            }
            .disabled(selectedProject == nil)
          }
        #else
          ToolbarItemGroup(placement: .navigationBarLeading) {
            Button("Экспортировать") {
              exportSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Импортировать") {
              importSelectedProject()
            }
            .disabled(selectedProject == nil)
          }
        #endif
      }
    } detail: {
      if let project = selectedProject {
        ProjectDetailView(project: project)
      } else {
        Text("Выберите проект")
          .foregroundColor(.gray)
      }
    }
    .navigationDestination(for: WritingProject.self) { project in
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
    .sheet(isPresented: $showingAddProject) {
      AddProjectView()
    }
    .sheet(isPresented: $showArchivedList) {
      ArchivedProjectsView()
    }
    .alert(isPresented: $showArchiveAlert) {
      Alert(
        title: Text("Архивировать проект \"\(projectToArchive?.title ?? "")\"?"),
        message: Text("Проект можно будет восстановить в любое время."),
        primaryButton: .destructive(Text("Архивировать")) {
          if let project = projectToArchive {
            archiveProject(project)
          }
        },
        secondaryButton: .cancel()
      )
    }
  }

  private func addProject() {
    showingAddProject = true
  }

  private func deleteSelectedProject() {
    guard let project = selectedProject else { return }
    confirmArchiveProject(project)
  }

  private func archiveProjects(at offsets: IndexSet) {
    if let index = offsets.first {
      confirmArchiveProject(projects[index])
    }
  }

  private func confirmArchiveProject(_ project: WritingProject) {
    projectToArchive = project
    showArchiveAlert = true
  }

  private func archiveProject(_ project: WritingProject) {
    project.isArchived = true
    try? modelContext.save()
    if selectedProject === project {
      selectedProject = nil
    }
  }

#if os(macOS)
  // MARK: - macOS File Operations
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

  // MARK: - Export
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

  // MARK: - Import
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
}
