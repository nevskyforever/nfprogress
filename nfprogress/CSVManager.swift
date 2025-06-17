import Foundation
import SwiftData

struct CSVManager {
    static func csvString(for project: WritingProject) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Date,CharacterCount,ChangeSinceLast,ProgressPercent"]
        let dateFormatter = ISO8601DateFormatter()
        let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
        if project.entries.isEmpty {
            lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,,")
        } else {
            var previous = 0
            for entry in project.allEntries {
                let dateStr = dateFormatter.string(from: entry.date)
                let change = entry.characterCount - previous
                previous = entry.characterCount
                let percent = Int(Double(entry.characterCount) / Double(max(project.goal, 1)) * 100)
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(dateStr),\(entry.characterCount),\(change),\(percent)")
            }
        }
        return lines.joined(separator: "\n")
    }

    static func csvString(for projects: [WritingProject]) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Date,CharacterCount,ChangeSinceLast,ProgressPercent"]
        let dateFormatter = ISO8601DateFormatter()
        for project in projects {
            let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
            if project.entries.isEmpty {
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,,")
            } else {
                var previous = 0
                for entry in project.allEntries {
                    let dateStr = dateFormatter.string(from: entry.date)
                    let change = entry.characterCount - previous
                    previous = entry.characterCount
                    let percent = Int(Double(entry.characterCount) / Double(max(project.goal, 1)) * 100)
                    lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(dateStr),\(entry.characterCount),\(change),\(percent)")
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
            guard components.count >= 5 else { continue }
            let title = components[0]
            let goal = Int(components[1]) ?? 0
            let deadlineStr = components[2]
            let dateStr = components[3]
            let count = Int(components[4]) ?? 0

            let project: WritingProject
            if let existing = projectsDict[title] {
                project = existing
            } else {
                let deadline = dateFormatter.date(from: deadlineStr)
                project = WritingProject(title: title, goal: goal, deadline: deadline)
                projectsDict[title] = project
            }

            if let date = dateFormatter.date(from: dateStr) {
                let entry = Entry(date: date, characterCount: count)
                project.entries.append(entry)
            }
        }
        return Array(projectsDict.values)
    }

    // MARK: - Helpers
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
