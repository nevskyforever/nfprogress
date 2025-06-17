import SwiftUI
import Charts

struct ProgressChartView: View {
    var project: WritingProject

    var body: some View {
        if project.sortedEntries.count >= 2 {
            VStack(alignment: .leading, spacing: 8) {
                Text("📈 График прогресса")
                    .font(.headline)

                Text("🔥 Стик: \(project.streak) дней подряд")
                    .font(.subheadline)
                    .foregroundColor(.green)

                if let message = project.streakMessage {
                    Text(message)
                        .font(.footnote)
                        .foregroundColor(.orange)
                }

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
            .padding(.top)
        }
    }
}
