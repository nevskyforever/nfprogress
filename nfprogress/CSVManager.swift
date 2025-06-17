import Foundation
import SwiftData

struct CSVManager {
    static func csvString(for project: WritingProject) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Date,CharacterCount"]
        let dateFormatter = ISO8601DateFormatter()
        let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
        if project.entries.isEmpty {
            lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,")
        } else {
            for entry in project.sortedEntries {
                let dateStr = dateFormatter.string(from: entry.date)
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(dateStr),\(entry.characterCount)")
            }
        }
        return lines.joined(separator: "\n")
    }

    static func csvString(for projects: [WritingProject]) -> String {
        var lines: [String] = ["Title,Goal,Deadline,Date,CharacterCount"]
        let dateFormatter = ISO8601DateFormatter()
        for project in projects {
            let deadlineString = project.deadline.map { dateFormatter.string(from: $0) } ?? ""
            if project.entries.isEmpty {
                lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),,")
            } else {
                for entry in project.sortedEntries {
                    let dateStr = dateFormatter.string(from: entry.date)
                    lines.append("\(escape(project.title)),\(project.goal),\(deadlineString),\(dateStr),\(entry.characterCount)")
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
        if string.contains(where: { $0 == "," || $0 == "\"" || $0 == "\n" }) {
            let escaped = string.replacingOccurrences(of: "\"", with: "\"\"")
            return "\"\(escaped)\""
        }
        return string
    }

    private static func parseCSVLine(_ line: String) -> [String] {
        var result: [String] = []
        var current = ""
        let chars = Array(line)
        var index = 0
        var inQuotes = false
        while index < chars.count {
            let char = chars[index]
            if char == "\"" {
                if inQuotes && index + 1 < chars.count && chars[index + 1] == "\"" {
                    current.append("\"")
                    index += 1
                } else {
                    inQuotes.toggle()
                }
            } else if char == "," && !inQuotes {
                result.append(current)
                current = ""
            } else {
                current.append(char)
            }
            index += 1
        }
        result.append(current)
        return result
    }
}
