#if canImport(SwiftUI)
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    @State private var intervalText: String = ""
    private let viewSpacing: CGFloat = scaledSpacing(2)
    /// "38" приблизительно соответствует прежней ширине 300pt,
    /// кратной шагу компоновки.
    private let minWidth: CGFloat = layoutStep(38)
    private let minHeight: CGFloat = layoutStep(25)
    /// Фиксированная ширина для подписи настройки,
    /// чтобы переключатели располагались на одном уровне
    private let labelWidth: CGFloat = layoutStep(30)

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {
            Text("appearance")
                .font(.headline)

            HStack {
                Text("language")
                    .frame(width: labelWidth, alignment: .leading)
                Picker("", selection: $settings.language) {
                    ForEach(AppLanguage.allCases) { lang in
                        Text(lang.description).tag(lang)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .fixedSize()
            }

            Toggle(isOn: $settings.disableLaunchAnimations) {
                Text("disable_launch_animations")
                    .frame(width: labelWidth, alignment: .leading)
            }
            .toggleStyle(.switch)

            Toggle(isOn: $settings.disableAllAnimations) {
                Text("disable_all_animations")
                    .frame(width: labelWidth, alignment: .leading)
            }
            .toggleStyle(.switch)

            Toggle(isOn: $settings.pauseAllSync) {
                Text("pause_sync_all")
                    .frame(width: labelWidth, alignment: .leading)
            }
            .toggleStyle(.switch)

            HStack {
                Text(settings.localized("sync_interval_prefix"))
                    .frame(width: labelWidth, alignment: .leading)
                SelectAllIntField(text: $intervalText, placeholder: "interval")
                    .frame(width: layoutStep(10))
                Text(settings.localized("sync_interval_suffix"))
            }
            .onAppear { intervalText = String(Int(settings.syncInterval)) }
            .onDisappear {
                if let val = Double(intervalText) { settings.syncInterval = val }
            }

            Toggle(isOn: $settings.deadlineReminders) {
                Text("deadline_reminders")
                    .frame(width: labelWidth, alignment: .leading)
            }
            .toggleStyle(.switch)

            if settings.deadlineReminders {
                HStack {
                    Text("reminder_time")
                        .frame(width: labelWidth, alignment: .leading)
                    DatePicker("", selection: $settings.reminderTime, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                }

                Toggle(isOn: $settings.remindersOnLaunch) {
                    Text("reminders_on_launch")
                        .frame(width: labelWidth, alignment: .leading)
                }
                .toggleStyle(.switch)
            }

            Spacer()
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
    }
}
#endif
