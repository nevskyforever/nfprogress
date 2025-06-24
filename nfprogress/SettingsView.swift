#if canImport(SwiftUI)
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    private let viewSpacing: CGFloat = scaledSpacing(2)
    /// "38" приблизительно соответствует прежней ширине 300pt,
    /// кратной шагу компоновки.
    private let minWidth: CGFloat = layoutStep(38)
    private let minHeight: CGFloat = layoutStep(25)

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {
            Text("appearance")
                .font(.headline)

            Picker("language", selection: $settings.language) {
                ForEach(AppLanguage.allCases) { lang in
                    Text(lang.description).tag(lang)
                }
            }
            .pickerStyle(.segmented)

            Toggle("disable_launch_animations", isOn: $settings.disableLaunchAnimations)

            Toggle("disable_all_animations", isOn: $settings.disableAllAnimations)

            Spacer()
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
    }
}
#endif
