import SwiftUI
import SwiftData

struct ArchivedProjectsView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Query(filter: #Predicate<WritingProject> { $0.isArchived })
    private var archived: [WritingProject]

    var body: some View {
        VStack(spacing: 16) {
            Text("Архивированные проекты")
                .font(.title2.bold())
            if archived.isEmpty {
                Text("Архив пуст")
                    .foregroundColor(.gray)
            } else {
                List {
                    ForEach(archived, id: \.id) { project in
                        HStack {
                            Text(project.title)
                            Spacer()
                            Button("Восстановить") {
                                project.isArchived = false
                                try? modelContext.save()
                            }
                            Button(role: .destructive) {
                                modelContext.delete(project)
                                try? modelContext.save()
                            } label: {
                                Text("Удалить")
                            }
                        }
                    }
                }
                .frame(maxHeight: 300)
            }
            Button("Закрыть") {
                dismiss()
            }
            .padding(.top)
        }
        .padding()
        .frame(width: 320)
        .onAppear {
            print("Archived projects count: \(archived.count)")
        }
    }
}

