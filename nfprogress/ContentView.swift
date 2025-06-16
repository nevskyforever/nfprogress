import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var projects: [WritingProject]

    var body: some View {
        NavigationSplitView {
            List {
                ForEach(projects) { project in
                    NavigationLink {
                        ProjectDetailView(project: project)
                    } label: {
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
            }
        } detail: {
            Text("Выберите проект")
                .foregroundColor(.gray)
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
}
