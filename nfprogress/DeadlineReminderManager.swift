#if canImport(UserNotifications) && canImport(SwiftData)
import Foundation
import UserNotifications
import SwiftData

@MainActor
enum DeadlineReminderManager {
    private static var enabled: Bool = false
    private static var time: Date = .now

    static func updateSettings(enabled: Bool, time: Date) {
        self.enabled = enabled
        self.time = time
        scheduleReminders()
    }

    static func scheduleReminders() {
        let center = UNUserNotificationCenter.current()
        center.removeAllPendingNotificationRequests()
        guard enabled else { return }
        center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
            guard granted else { return }
            schedule(for: center)
        }
    }

    static func sendMissedRemindersIfNeeded() {
        let center = UNUserNotificationCenter.current()
        guard enabled else { return }
        let calendar = Calendar.current
        let comps = calendar.dateComponents([.hour, .minute], from: time)
        guard let scheduled = calendar.date(bySettingHour: comps.hour ?? 0,
                                            minute: comps.minute ?? 0,
                                            second: 0,
                                            of: Date()) else { return }
        guard Date() > scheduled else { return }
        center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
            guard granted else { return }
            deliverNow(for: center)
        }
    }

    private static func schedule(for center: UNUserNotificationCenter) {
        let context = DataController.mainContext
        let descriptor = FetchDescriptor<WritingProject>()
        if let projects = try? context.fetch(descriptor) {
            for project in projects {
                guard project.deadline != nil,
                      let target = project.dailyTarget,
                      project.goal > project.currentProgress else { continue }
                var comps = DateComponents()
                let t = Calendar.current.dateComponents([.hour, .minute], from: time)
                comps.hour = t.hour
                comps.minute = t.minute
                comps.timeZone = Calendar.current.timeZone
                let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: true)
                let content = UNMutableNotificationContent()
                content.title = project.title
                content.body = String(format: NSLocalizedString("deadline_reminder_body", comment: ""), target)
                content.sound = .default
                let identifier = String(describing: project.id)
                let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
                center.add(request)
            }
        }
    }

    private static func deliverNow(for center: UNUserNotificationCenter) {
        let context = DataController.mainContext
        let descriptor = FetchDescriptor<WritingProject>()
        if let projects = try? context.fetch(descriptor) {
            for project in projects {
                guard project.deadline != nil,
                      let target = project.dailyTarget,
                      project.goal > project.currentProgress else { continue }
                let content = UNMutableNotificationContent()
                content.title = project.title
                content.body = String(format: NSLocalizedString("deadline_reminder_body", comment: ""), target)
                content.sound = .default
                let request = UNNotificationRequest(identifier: UUID().uuidString,
                                                   content: content,
                                                   trigger: nil)
                center.add(request)
            }
        }
    }
}
#endif
