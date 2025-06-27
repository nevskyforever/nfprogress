import Foundation
#if canImport(SwiftData)
import SwiftData

struct CSVManager {
    static func csvString(for project: WritingProject) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Stage,StageGoal,StageDeadline,StageStart,Date,CharacterCount,ChangeSinceLast,ProgressPercent"]
        let dateFormatter = ISO8601DateFormatter()
        let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
        var all: [(Entry, Stage?)] = project.entries.map { ($0, nil) }
        var emptyStages: [Stage] = []
        for stage in project.stages {
            if stage.entries.isEmpty {
                emptyStages.append(stage)
            } else {
                for e in stage.entries { all.append((e, stage)) }
            }
        }
        if all.isEmpty && emptyStages.isEmpty {
            lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,,,,,")
        } else {
            let sorted = all.sorted { $0.0.date < $1.0.date }
            var cumulative = 0
            for (entry, stage) in sorted {
                let dateStr = dateFormatter.string(from: entry.date)
                cumulative += entry.characterCount
                let total = cumulative
                let change = entry.characterCount
                let percent = Int(Double(total) / Double(max(project.goal, 1)) * 100)
                let stageTitle = stage?.title ?? ""
                let stageGoal = stage != nil ? String(stage!.goal) : ""
                let stageDeadline = stage?.deadline.map { dateFormatter.string(from: $0) } ?? ""
                let stageStart = stage != nil ? String(stage!.startProgress) : ""
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(escape(stageTitle)),\(stageGoal),\(stageDeadline),\(stageStart),\(dateStr),\(total),\(change),\(percent)")
            }
            for stage in emptyStages {
                let stageDeadline = stage.deadline.map { dateFormatter.string(from: $0) } ?? ""
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(escape(stage.title)),\(stage.goal),\(stageDeadline),\(stage.startProgress),,,,")
            }
        }
        return lines.joined(separator: "\n")
    }

    static func csvString(for projects: [WritingProject]) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Stage,StageGoal,StageDeadline,StageStart,Date,CharacterCount,ChangeSinceLast,ProgressPercent"]
        let dateFormatter = ISO8601DateFormatter()
        for project in projects {
            let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
            var all: [(Entry, Stage?)] = project.entries.map { ($0, nil) }
            var emptyStages: [Stage] = []
            for stage in project.stages {
                if stage.entries.isEmpty {
                    emptyStages.append(stage)
                } else {
                    for e in stage.entries { all.append((e, stage)) }
                }
            }
            if all.isEmpty && emptyStages.isEmpty {
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,,,,,")
            } else {
                let sorted = all.sorted { $0.0.date < $1.0.date }
                var cumulative = 0
                for (entry, stage) in sorted {
                    let dateStr = dateFormatter.string(from: entry.date)
                    cumulative += entry.characterCount
                    let total = cumulative
                    let change = entry.characterCount
                    let percent = Int(Double(total) / Double(max(project.goal, 1)) * 100)
                    let stageTitle = stage?.title ?? ""
                    let stageGoal = stage != nil ? String(stage!.goal) : ""
                    let stageDeadline = stage?.deadline.map { dateFormatter.string(from: $0) } ?? ""
                    let stageStart = stage != nil ? String(stage!.startProgress) : ""
                    lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(escape(stageTitle)),\(stageGoal),\(stageDeadline),\(stageStart),\(dateStr),\(total),\(change),\(percent)")
                }
                for stage in emptyStages {
                    let stageDeadline = stage.deadline.map { dateFormatter.string(from: $0) } ?? ""
                    lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(escape(stage.title)),\(stage.goal),\(stageDeadline),\(stage.startProgress),,,,")
                }
            }
        }
        return lines.joined(separator: "\n")
    }

    static func importProjects(from csv: String) -> [WritingProject] {
        let lines = csv.components(separatedBy: "\n").dropFirst()
        var projectsDict: [String: WritingProject] = [:]
        let dateFormatter = ISO8601DateFormatter()
        for line in lines where !line.trimmingCharacters(in: .whitespaces).isEmpty {
            let components = parseCSVLine(line)
            guard components.count >= 9 else { continue }
            let title = components[0]
            let goal = Int(components[1]) ?? 0
            let deadlineStr = components[2]
            let stageTitle = components[3]
            let stageGoal = Int(components[4]) ?? 0
            let stageDeadlineStr = components[5]
            let stageStart = Int(components[6]) ?? 0
            let dateStr = components[7]
            let count = Int(components[8]) ?? 0

            let project: WritingProject
            if let existing = projectsDict[title] {
                project = existing
            } else {
                let deadline = dateFormatter.date(from: deadlineStr)
                project = WritingProject(title: title, goal: goal, deadline: deadline, order: projectsDict.count)
                projectsDict[title] = project
            }

            var stage: Stage? = nil
            if !stageTitle.isEmpty {
                if let existing = project.stages.first(where: { $0.title == stageTitle }) {
                    stage = existing
                } else {
                    let stageDeadline = dateFormatter.date(from: stageDeadlineStr)
                    let newStage = Stage(title: stageTitle, goal: stageGoal, deadline: stageDeadline, startProgress: stageStart)
                    project.stages.append(newStage)
                    stage = newStage
                }
            }

            if let date = dateFormatter.date(from: dateStr) {
                let entry = Entry(date: date, characterCount: count)
                if let stage {
                    stage.entries.append(entry)
                } else {
                    project.entries.append(entry)
                }
            }
        }
        return Array(projectsDict.values)
    }

    // MARK: - Экспорт/Импорт JSON

    struct JSONEntry: Codable {
        var date: Date
        var characterCount: Int
    }

    struct JSONStage: Codable {
        var title: String
        var goal: Int
        var deadline: Date?
        var startProgress: Int
        var entries: [JSONEntry]
    }

    struct JSONProject: Codable {
        var title: String
        var goal: Int
        var deadline: Date?
        var entries: [JSONEntry]
        var stages: [JSONStage]
    }

    static func jsonData(for project: WritingProject) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        let p = JSONProject(
            title: project.title,
            goal: project.goal,
            deadline: project.deadline,
            entries: project.entries.map { JSONEntry(date: $0.date, characterCount: $0.characterCount) },
            stages: project.stages.map { stage in
                JSONStage(
                    title: stage.title,
                    goal: stage.goal,
                    deadline: stage.deadline,
                    startProgress: stage.startProgress,
                    entries: stage.entries.map { JSONEntry(date: $0.date, characterCount: $0.characterCount) }
                )
            }
        )
        return try encoder.encode(p)
    }

    static func projects(fromJSON data: Data) throws -> [WritingProject] {
        let decoder = JSONDecoder()
        let projectsData = try decoder.decode([JSONProject].self, from: data)
        return projectsData.enumerated().map { idx, jp in
            let proj = WritingProject(title: jp.title, goal: jp.goal, deadline: jp.deadline, order: idx)
            proj.entries = jp.entries.map { Entry(date: $0.date, characterCount: $0.characterCount) }
            proj.stages = jp.stages.map { js in
                let st = Stage(title: js.title, goal: js.goal, deadline: js.deadline, startProgress: js.startProgress)
                st.entries = js.entries.map { Entry(date: $0.date, characterCount: $0.characterCount) }
                return st
            }
            return proj
        }
    }

    // MARK: - Вспомогательные функции
    private static func escape(_ string: String) -> String {
        var escaped = string.replacingOccurrences(of: "\"", with: "\"\"")
        if escaped.contains(",") || escaped.contains("\"") || escaped.contains("\n") {
            escaped = "\"\(escaped)\""
        }
        return escaped
    }

    private static func parseCSVLine(_ line: String) -> [String] {
        var result: [String] = []
        var current = ""
        var inQuotes = false
        var index = line.startIndex
        while index < line.endIndex {
            let char = line[index]
            if char == "\"" {
                if inQuotes {
                    let nextIndex = line.index(after: index)
                    if nextIndex < line.endIndex && line[nextIndex] == "\"" {
                        current.append("\"")
                        index = nextIndex
                    } else {
                        inQuotes = false
                    }
                } else {
                    inQuotes = true
                }
            } else if char == "," && !inQuotes {
                result.append(current)
                current = ""
            } else {
                current.append(char)
            }
            index = line.index(after: index)
        }
        result.append(current)
        return result
    }
}
#endif
