import SwiftData
import SwiftUI
import UniformTypeIdentifiers
#if os(macOS)
import AppKit
#endif

struct ContentView: View {
  @Environment(\.modelContext) private var modelContext
  @Query(
    filter: #Predicate<WritingProject> { !$0.isStage },
    sort: [SortDescriptor(\.title)]
  )
  private var projects: [WritingProject]
  @State private var selectedProject: WritingProject?
  @State private var isExporting = false
  @State private var isImporting = false
  @State private var showingAddProject = false
  @State private var projectToDelete: WritingProject?
  @State private var showDeleteAlert = false
  @State private var expandedProjects: Set<UUID> = []

  var body: some View {
    NavigationSplitView {
      List(selection: $selectedProject) {
        ForEach(projects) { project in
          DisclosureGroup(isExpanded: binding(for: project)) {
            ForEach(project.stages) { stage in
              NavigationLink(value: stage) {
                VStack(alignment: .leading) {
                  Text(stage.title)
                    .font(.subheadline)
                  ProgressCircleView(project: stage)
                    .frame(height: 60)
                }
                .padding(.vertical, 2)
              }
            }
          } label: {
            NavigationLink(value: project) {
              VStack(alignment: .leading) {
                Text(project.title)
                  .font(.headline)
                ProgressCircleView(project: project)
                  .frame(height: 80)
              }
              .padding(.vertical, 4)
            }
          }
        }
        .onDelete(perform: deleteProjects)
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
            Label("Удалить", systemImage: "minus")
          }
          .keyboardShortcut(.return, modifiers: .command)
          .disabled(selectedProject == nil)
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
    .alert(isPresented: $showDeleteAlert) {
      Alert(
        title: Text("Удалить проект \"\(projectToDelete?.title ?? "")\"?"),
        message: Text("Это действие нельзя отменить."),
        primaryButton: .destructive(Text("Удалить")) {
          if let project = projectToDelete {
            deleteProject(project)
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
    confirmDeleteProject(project)
  }

  private func deleteProjects(at offsets: IndexSet) {
    if let index = offsets.first, index < projects.count {
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
  }

  private func binding(for project: WritingProject) -> Binding<Bool> {
    Binding(
      get: { expandedProjects.contains(project.id) },
      set: { newValue in
        if newValue { expandedProjects.insert(project.id) }
        else { expandedProjects.remove(project.id) }
      }
    )
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
