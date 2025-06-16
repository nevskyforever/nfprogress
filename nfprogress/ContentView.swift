import SwiftData
import SwiftUI
import UniformTypeIdentifiers
#if os(macOS)
import AppKit
#endif

struct ContentView: View {
  @Environment(\.modelContext) private var modelContext
  @Query private var projects: [WritingProject]
  @State private var selectedProject: WritingProject?
  @State private var isExporting = false
  @State private var exportAllMode = false
  @State private var isImporting = false

  var body: some View {
    NavigationSplitView {
      List(selection: $selectedProject) {
        ForEach(projects) { project in
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
        .onDelete(perform: deleteProjects)
      }
      .navigationTitle("Мои тексты")
      .toolbar {
        ToolbarItem {
          Button(action: addProject) {
            Label("Добавить", systemImage: "plus")
          }
        }
        #if os(macOS)
          ToolbarItemGroup(placement: .navigation) {
            Button("Экспортировать") {
              exportSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Экспортировать все") {
              exportAllProjects()
            }
            Button("Импортировать") {
              importSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Импортировать все") {
              importAllProjects()
            }
          }
        #else
          ToolbarItemGroup(placement: .navigationBarLeading) {
            Button("Экспортировать") {
              exportSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Экспортировать все") {
              exportAllProjects()
            }
            Button("Импортировать") {
              importSelectedProject()
            }
            .disabled(selectedProject == nil)
            Button("Импортировать все") {
              importAllProjects()
            }
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
  }

  private func addProject() {
    let newProject = WritingProject(title: "Новый текст", goal: 10000)
    modelContext.insert(newProject)
  }

  private func deleteProjects(at offsets: IndexSet) {
    for index in offsets {
      modelContext.delete(projects[index])
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
    exportAllMode = false
#if os(macOS)
    showSavePanel()
#else
    isExporting = true
#endif
  }

  private func exportAllProjects() {
    exportAllMode = true
#if os(macOS)
    showSavePanel()
#else
    isExporting = true
#endif
  }

  private var exportDocument: CSVDocument {
    let csv: String
    if exportAllMode {
      csv = CSVManager.csvString(for: projects)
    } else if let project = selectedProject {
      csv = CSVManager.csvString(for: project)
    } else {
      csv = ""
    }
    return CSVDocument(text: csv)
  }

  private var exportFileName: String {
    let base: String
    if exportAllMode {
      base = "AllProjects"
    } else if let project = selectedProject {
      base = project.title.replacingOccurrences(of: " ", with: "_")
    } else {
      base = "Project"
    }
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

  private func importAllProjects() {
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
