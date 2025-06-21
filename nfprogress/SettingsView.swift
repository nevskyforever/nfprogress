#if canImport(SwiftUI)
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    private let viewSpacing: CGFloat = scaledSpacing(2)
    /// "38" approximates the previous 300pt width with whole layout steps.
    private let minWidth: CGFloat = layoutStep(38)
    private let minHeight: CGFloat = layoutStep(25)

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {
            Text("Внешний вид")
                .font(.headline)

            Toggle("Отключить анимации при запуске", isOn: $settings.disableLaunchAnimations)

            Toggle("Отключить все анимации", isOn: $settings.disableAllAnimations)

            Spacer()
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
    }
}
#endif
