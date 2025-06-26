#if canImport(SwiftUI)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif
import UniformTypeIdentifiers
#if os(iOS)
import UIKit
#elseif os(macOS)
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
  /// Проект, открытый в навигационном стеке на iPhone
  @State private var openedProject: WritingProject?
  @State private var isExporting = false
  @State private var isImporting = false
  @State private var showingAddProject = false
  @State private var projectToDelete: WritingProject?
  @State private var showDeleteAlert = false
#if os(iOS)
  @State private var editMode: EditMode = .inactive
#endif
#if os(macOS)
  @AppStorage("sidebarWidth") private var sidebarWidthRaw: Double = 405
  private var sidebarWidth: CGFloat {
    get { CGFloat(sidebarWidthRaw) }
    nonmutating set { sidebarWidthRaw = Double(newValue) }
  }
#endif

  private let circleHeight: CGFloat = layoutStep(10)
#if os(macOS)
  /// Минимальная ширина основного окна
  private let minWindowWidth: CGFloat = layoutStep(48)
#endif
#if os(iOS)
  /// Увеличенный размер круга при отображении проектов в меню
  private let largeCircleHeight: CGFloat = layoutStep(20)
#endif


  private var sortedProjects: [WritingProject] {
    switch settings.projectSortOrder {
    case .title:
      return projects.sorted { $0.title.localizedCompare($1.title) == .orderedAscending }
    case .progress:
      return projects.sorted { $0.progress > $1.progress }
    case .custom:
      return projects
    }
  }

  private var splitView: some View {
#if os(iOS)
    Group {
      if UIDevice.current.userInterfaceIdiom == .pad {
        NavigationSplitView(sidebar: {
          List {
            let count = sortedProjects.count
            ForEach(Array(sortedProjects.enumerated()), id: \.element) { index, project in
              projectRow(for: project, index: index, totalCount: count)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, scaledSpacing(1))
                .frame(minHeight: circleHeight + layoutStep(2))
                .contentShape(Rectangle())
                .onTapGesture { selectedProject = project }
                .listRowInsets(EdgeInsets())
            }
            .onDelete(perform: deleteProjects)
            .onMove(perform: moveProjects)
            .moveDisabled(settings.projectSortOrder != .custom)
          }
          #if os(iOS)
          .environment(\.editMode, $editMode)
          #endif
          .listStyle(.plain)
          .navigationTitle("my_texts")
          .toolbar { toolbarContent }
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
      } else {
        NavigationStack {
          List {
            let count = sortedProjects.count
            ForEach(Array(sortedProjects.enumerated()), id: \.element) { index, project in
              projectRow(for: project, index: index, totalCount: count)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, scaledSpacing(1))
                .frame(minHeight: (settings.projectListStyle == .detailed ? largeCircleHeight : circleHeight) + layoutStep(2))
                .contentShape(Rectangle())
                .onTapGesture {
                  if selectedProject === project {
                    openedProject = project
                  } else {
                    selectedProject = project
                  }
                }
                .listRowInsets(EdgeInsets())
                .listRowBackground(selectedProject === project ? Color.accentColor.opacity(0.1) : Color.clear)
            }
            .onDelete(perform: deleteProjects)
            .onMove(perform: moveProjects)
            .moveDisabled(settings.projectSortOrder != .custom)
          }
          #if os(iOS)
          .environment(\.editMode, $editMode)
          #endif
          .listStyle(.plain)
          .navigationTitle("my_texts")
          .navigationBarTitleDisplayMode(.inline)
          .toolbar { toolbarContent }
          .navigationDestination(item: $openedProject) { project in
            ProjectDetailView(project: project)
          }
        }
      }
    }
#else
    NavigationSplitView(sidebar: {
      List {
        let count = sortedProjects.count
        ForEach(Array(sortedProjects.enumerated()), id: \.element) { index, project in
          projectRow(for: project, index: index, totalCount: count)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, scaledSpacing(1))
            .frame(minHeight: circleHeight + layoutStep(2))
            .contentShape(Rectangle())
            .onTapGesture { selectedProject = project }
            .listRowInsets(EdgeInsets())
        }
        .onDelete(perform: deleteProjects)
        .onMove(perform: moveProjects)
        .moveDisabled(settings.projectSortOrder != .custom)
      }
      .listStyle(.plain)
      .navigationTitle("my_texts")
      .toolbar { fixedToolbarContent }
      .toolbar(id: "mainToolbar") { customizableToolbarContent }
    }, detail: {
      if let project = selectedProject {
        ProjectDetailView(project: project)
      } else {
        Text("select_project")
          .foregroundColor(.gray)
      }
    })
#if os(macOS)
    .navigationSplitViewColumnWidth(min: minWindowWidth, ideal: sidebarWidth, max: .infinity)
    .persistentSidebarWidth()
#endif
    .navigationDestination(for: WritingProject.self) { project in
      ProjectDetailView(project: project)
    }
#endif
  }

  @ViewBuilder
  private func projectRow(for project: WritingProject, index: Int, totalCount: Int) -> some View {
    switch settings.projectListStyle {
    case .detailed:
      VStack(alignment: .leading) {
        Text(project.title)
          .font(.headline)
          .frame(maxWidth: .infinity, alignment: .leading)
          .fixedSize(horizontal: false, vertical: true)
        HStack {
          Spacer()
#if os(iOS)
          ProgressCircleView(project: project, index: index, totalCount: totalCount, style: .large)
            .frame(height: largeCircleHeight)
#else
          ProgressCircleView(project: project, index: index, totalCount: totalCount)
            .frame(height: circleHeight)
#endif
          Spacer()
        }
      }
    case .compact:
      CompactProjectRow(project: project, index: index, totalCount: totalCount)
    }
  }

  #if os(macOS)
  // Элементы панели, которые нельзя удалить
  @ToolbarContentBuilder
  private var fixedToolbarContent: some ToolbarContent {
    ToolbarItem(id: "add", placement: .automatic) {
      Button(action: addProject) {
        Label("add", systemImage: "plus")
      }
      .keyboardShortcut("N", modifiers: [.command, .shift])
      .help(settings.localized("add_project_tooltip"))
    }

    ToolbarItem(id: "delete", placement: .automatic) {
      Button(action: deleteSelectedProject) {
        Label("delete", systemImage: "minus")
      }
      .keyboardShortcut(.return, modifiers: .command)
      .help(settings.localized("delete_project_tooltip"))
      .disabled(selectedProject == nil)
    }
  }

  // Кастомизируемые элементы панели
  @ToolbarContentBuilder
  private var customizableToolbarContent: some CustomizableToolbarContent {
    ToolbarItem(id: "import", placement: .automatic) {
      Button(action: {
        guard selectedProject != nil else { return }
        importSelectedProject()
      }) {
        Image(systemName: "square.and.arrow.down")
      }
      .accessibilityLabel(settings.localized("import"))
      .help(settings.localized("import_project_tooltip"))
    }

    ToolbarItem(id: "export", placement: .automatic) {
      Button(action: {
        guard selectedProject != nil else { return }
        exportSelectedProject()
      }) {
        Image(systemName: "square.and.arrow.up")
      }
      .accessibilityLabel(settings.localized("export"))
      .help(settings.localized("export_project_tooltip"))
    }

    ToolbarItem(id: "toggleView", placement: .automatic) {
      Button {
        settings.projectListStyle = settings.projectListStyle == .detailed ? .compact : .detailed
      } label: {
        Image(systemName: settings.projectListStyle == .detailed ? "chart.pie" : "list.bullet")
      }
      .help(settings.localized("toggle_view_tooltip"))
    }

    ToolbarItem(id: "toggleSort", placement: .automatic) {
      Button { settings.projectSortOrder = settings.projectSortOrder.next } label: {
        Image(systemName: settings.projectSortOrder.iconName)
      }
      .help(settings.localized("toggle_sort_tooltip"))
    }
  }
  #else
  @ToolbarContentBuilder
  private var toolbarContent: some ToolbarContent {
#if os(iOS)
    if UIDevice.current.userInterfaceIdiom == .pad {
      ToolbarItem(placement: .navigationBarTrailing) {
        HStack {
          Button(action: addProject) {
            Label("add", systemImage: "plus")
          }
          .keyboardShortcut("N", modifiers: [.command, .shift])
          .help(settings.localized("add_project_tooltip"))

          if selectedProject != nil {
            Button(action: deleteSelectedProject) {
              Label("delete", systemImage: "minus")
            }
            .keyboardShortcut(.return, modifiers: .command)
            .help(settings.localized("delete_project_tooltip"))
          }

          Button(action: importSelectedProject) {
            Image(systemName: "square.and.arrow.down")
          }
          .accessibilityLabel(settings.localized("import"))
          .help(settings.localized("import_project_tooltip"))

          if selectedProject != nil {
            Button(action: exportSelectedProject) {
              Image(systemName: "square.and.arrow.up")
            }
            .accessibilityLabel(settings.localized("export"))
            .help(settings.localized("export_project_tooltip"))

            Button {
              settings.projectListStyle = settings.projectListStyle == .detailed ? .compact : .detailed
            } label: {
              Image(systemName: settings.projectListStyle == .detailed ? "chart.pie" : "list.bullet")
            }
            .help(settings.localized("toggle_view_tooltip"))

            Button { settings.projectSortOrder = settings.projectSortOrder.next } label: {
              Image(systemName: settings.projectSortOrder.iconName)
            }
            .help(settings.localized("toggle_sort_tooltip"))
          }
        }
      }
    } else {
      ToolbarItem(placement: .navigationBarTrailing) {
        Menu {
          if selectedProject != nil {
            Button(action: importSelectedProject) {
              Label(settings.localized("import"), systemImage: "square.and.arrow.down")
            }

            Button(action: exportSelectedProject) {
              Label(settings.localized("export"), systemImage: "square.and.arrow.up")
            }
          }

          Button {
            settings.projectListStyle = settings.projectListStyle == .detailed ? .compact : .detailed
          } label: {
            Label(settings.localized("toggle_view_tooltip"), systemImage: settings.projectListStyle == .detailed ? "chart.pie" : "list.bullet")
          }

          Button { settings.projectSortOrder = settings.projectSortOrder.next } label: {
            Label(settings.localized("toggle_sort_tooltip"), systemImage: settings.projectSortOrder.iconName)
          }
        } label: {
          Image(systemName: "ellipsis.circle")
        }
      }
      ToolbarItem(placement: .primaryAction) {
        Button(action: addProject) {
          Label("add", systemImage: "plus")
        }
        .keyboardShortcut("N", modifiers: [.command, .shift])
        .help(settings.localized("add_project_tooltip"))
      }
      if selectedProject != nil {
        ToolbarItem(placement: .primaryAction) {
          Button(action: deleteSelectedProject) {
            Label("delete", systemImage: "minus")
          }
          .keyboardShortcut(.return, modifiers: .command)
          .help(settings.localized("delete_project_tooltip"))
        }
      }
    }
#else
    ToolbarItemGroup(placement: .automatic) {
      Button(action: addProject) {
        Label("add", systemImage: "plus")
      }
      .keyboardShortcut("N", modifiers: [.command, .shift])
      .help(settings.localized("add_project_tooltip"))

      if selectedProject != nil {
        Button(action: deleteSelectedProject) {
          Label("delete", systemImage: "minus")
        }
        .keyboardShortcut(.return, modifiers: .command)
        .help(settings.localized("delete_project_tooltip"))
      }

      Button(action: importSelectedProject) {
        Image(systemName: "square.and.arrow.down")
      }
      .accessibilityLabel(settings.localized("import"))
      .help(settings.localized("import_project_tooltip"))

      if selectedProject != nil {
        Button(action: exportSelectedProject) {
          Image(systemName: "square.and.arrow.up")
        }
        .accessibilityLabel(settings.localized("export"))
        .help(settings.localized("export_project_tooltip"))

        Button {
          settings.projectListStyle = settings.projectListStyle == .detailed ? .compact : .detailed
        } label: {
          Image(systemName: settings.projectListStyle == .detailed ? "chart.pie" : "list.bullet")
        }
        .help(settings.localized("toggle_view_tooltip"))

        Button { settings.projectSortOrder = settings.projectSortOrder.next } label: {
          Image(systemName: settings.projectSortOrder.iconName)
        }
        .help(settings.localized("toggle_sort_tooltip"))
      }
    }
#endif
  }
  #endif

  var body: some View {
    splitView
#if os(iOS)
      .environment(\.editMode, $editMode)
#endif
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
    #if os(iOS)
    .onChange(of: settings.projectSortOrder) { newValue in
      editMode = newValue == .custom ? .active : .inactive
    }
    #endif
#if os(macOS)
    .onExitCommand { selectedProject = nil }
    .windowMinWidth(minWindowWidth)
    .onAppear { settings.applyToolbarCustomization() }
    .onChange(of: selectedProject) { _ in
      settings.applyToolbarCustomization()
    }
#endif
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
      let project = sortedProjects[index]
      confirmDeleteProject(project)
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
}
#endif
