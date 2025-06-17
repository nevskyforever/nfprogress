import SwiftUI
import Charts

struct ProgressChartView: View {
    var project: WritingProject

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("📈 График прогресса")
                .font(.headline)

            if let prompt = project.streakPrompt {
                Text(prompt)
                    .font(.subheadline)
                    .foregroundColor(.green)
            } else if project.streak == 0 {
                Text("Начнем путь к цели?")
                    .font(.subheadline)
                    .foregroundColor(.green)
            } else {
                Text("🔥 В цели \(project.streak) дней подряд")
                    .font(.subheadline)
                    .foregroundColor(.green)
            }

            if project.sortedEntries.count >= 2 {
                Chart {
                    // Целевая линия
                    RuleMark(y: .value("Цель", project.goal))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                        .foregroundStyle(.gray)
                        .annotation(position: .top, alignment: .leading) {
                            Text("Цель: \(project.goal)")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }

                    // Линия прогресса
                    ForEach(project.sortedEntries) { entry in
                        LineMark(
                            x: .value("Дата", entry.date),
                            y: .value("Символы", entry.characterCount)
                        )
                        .interpolationMethod(.monotone)
                        .symbol(.circle)
                        .foregroundStyle(.blue)
                    }
                }
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        if let date = value.as(Date.self) {
                            AxisGridLine()
                            AxisTick()
                            AxisValueLabel {
                                Text(date.formatted(date: .numeric, time: .shortened))
                            }
                        }
                    }
                }
                .frame(height: 200)
            }
        }
        .padding(.top)
    }
}
