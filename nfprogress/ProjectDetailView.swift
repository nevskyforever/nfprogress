import SwiftUI
import SwiftData

struct ProjectDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Bindable var project: WritingProject
    @State private var showingAddEntry = false
    @State private var showingAddStage = false
    @State private var stageToDelete: Stage?
    @State private var showStageAlert = false
    @State private var editingEntry: Entry?
    @State private var tempDeadline: Date = Date()
    // Editing state for individual fields
    @State private var isEditingTitle = false
    @State private var isEditingGoal = false
    @State private var isEditingDeadline = false
    @FocusState private var focusedField: Field?

    // Formatter for displaying deadline in Russian
    private let deadlineFormatter: DateFormatter = {
        let df = DateFormatter()
        df.locale = Locale(identifier: "ru_RU")
        df.dateFormat = "d MMMM yyyy"
        return df
    }()

    private enum Field: Hashable {
        case title, goal, deadline
    }

    private func deadlineColor(daysLeft: Int) -> Color {
        let maxDays = 30.0
        let ratio = max(0, min(1, Double(daysLeft) / maxDays))
        // Hue from red (0) to green (0.33)
        let hue = ratio * 0.33
        return Color(hue: hue, saturation: 1, brightness: 1)
    }

    private func addEntry() {
        showingAddEntry = true
    }

    private func addStage() {
        showingAddStage = true
    }

    private func confirmDeleteStage(_ stage: Stage) {
        stageToDelete = stage
        showStageAlert = true
    }

    private func deleteStage(_ stage: Stage) {
        if let index = project.stages.firstIndex(where: { $0.id == stage.id }) {
            project.stages.remove(at: index)
        }
        modelContext.delete(stage)
        saveContext()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Название и цель проекта
                HStack {
                    Text("Название:")
                        .font(.title3.bold())
                    if isEditingTitle {
                        TextField("", text: $project.title)
                            .textFieldStyle(.roundedBorder)
                            .fixedSize()
                            .submitLabel(.done)
                            .focused($focusedField, equals: .title)
                            .onSubmit { focusedField = nil }
                    } else {
                        Text(project.title)
                            .onTapGesture {
                                isEditingTitle = true
                                focusedField = .title
                            }
                    }
                }
                HStack {
                    Text("Цель:")
                        .font(.title3.bold())
                    if isEditingGoal {
                        TextField("", value: $project.goal, formatter: NumberFormatter())
                            .textFieldStyle(.roundedBorder)
                            .fixedSize()
                            .submitLabel(.done)
                            .focused($focusedField, equals: .goal)
                            .onSubmit { focusedField = nil }
                    } else {
                        Text("\(project.goal)")
                            .onTapGesture {
                                isEditingGoal = true
                                focusedField = .goal
                            }
                    }
                }

                // Дедлайн
                HStack {
                    Text("Дедлайн:")
                        .font(.title3.bold())
                    if isEditingDeadline {
                        DatePicker(
                            "",
                            selection: $tempDeadline,
                            displayedComponents: .date
                        )
                        .labelsHidden()
                        .environment(\.locale, Locale(identifier: "ru_RU"))
                        .focused($focusedField, equals: .deadline)
                        .submitLabel(.done)
                        .onSubmit { focusedField = nil }
                    } else {
                        Text(
                            project.deadline.map { deadlineFormatter.string(from: $0) } ??
                                "Не установлен"
                        )
                        .onTapGesture {
                            tempDeadline = project.deadline ?? Date()
                            isEditingDeadline = true
                            focusedField = .deadline
                        }
                    }
                }

                if !isEditingDeadline && project.deadline != nil {
                    Button("Удалить дедлайн", role: .destructive) {
                        project.deadline = nil
                        saveContext()
                    }

                    Text("Осталось дней: \(project.daysLeft)")
                        .font(.subheadline)
                        .foregroundColor(deadlineColor(daysLeft: project.daysLeft))
                    if let target = project.dailyTarget {
                        Text("Ежедневная цель: \(target) символов")
                            .font(.title3.bold())
                            .foregroundColor(.white)
                    }
                }

                if let prompt = project.streakPrompt {
                    Text(prompt)
                        .font(.subheadline)
                        .foregroundColor(.green)
                } else {
                    Text(project.streakStatus)
                        .font(.subheadline)
                        .foregroundColor(.green)
                }

                // Действия с проектом
                HStack {
                    Button("Добавить запись") {
                        addEntry()
                    }
                    .keyboardShortcut("n", modifiers: .command)
                    Button("Добавить этап") {
                        addStage()
                    }
                    .keyboardShortcut("m", modifiers: .command)
                    Spacer()
                }

                if !project.stages.isEmpty {
                    Text("Этапы")
                        .font(.title3.bold())
                    ForEach(project.stages) { stage in
                        VStack(alignment: .leading) {
                            HStack {
                                Text(stage.title)
                                    .font(.headline)
                                Spacer()
                                Button(role: .destructive) {
                                    confirmDeleteStage(stage)
                                } label: {
                                    Image(systemName: "trash")
                                }
                            }
                            Text("Цель: \(stage.goal) знаков")
                                .font(.caption)
                        }
                    }
                }

                // История записей
                Text("История записей")
                    .font(.title3.bold())
                ProgressChartView(project: project)

                HistoryView(project: project, editingEntry: $editingEntry)
            }
            .padding()
        }
        .simultaneousGesture(
            TapGesture().onEnded { focusedField = nil }
        )
        .onAppear {
            if let dl = project.deadline {
                tempDeadline = dl
            }
        }
        .sheet(isPresented: $showingAddEntry) {
            AddEntryView(project: project)
        }
        .sheet(isPresented: $showingAddStage) {
            AddStageView(project: project)
        }
        .alert(isPresented: $showStageAlert) {
            Alert(
                title: Text("Удалить этап \"\(stageToDelete?.title ?? "")\"?"),
                message: Text("Это действие нельзя отменить."),
                primaryButton: .destructive(Text("Удалить")) {
                    if let stage = stageToDelete { deleteStage(stage) }
                },
                secondaryButton: .cancel()
            )
        }
        .sheet(item: $editingEntry) { entry in
            EditEntryView(entry: entry)
        }
        .onChange(of: focusedField) { newValue in
            if newValue != .title && isEditingTitle {
                isEditingTitle = false
                saveContext()
            }
            if newValue != .goal && isEditingGoal {
                isEditingGoal = false
                saveContext()
            }
            if newValue != .deadline && isEditingDeadline {
                project.deadline = tempDeadline
                isEditingDeadline = false
                saveContext()
            }
        }
    }

    // MARK: - Save Context
    private func saveContext() {
        do {
            try modelContext.save()
        } catch {
            print("Ошибка сохранения: \(error)")
        }
    }
}

