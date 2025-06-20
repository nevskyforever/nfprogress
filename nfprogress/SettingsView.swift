#if canImport(SwiftUI)
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    private let scaleOptions = TextScale.values

    @Environment(\.textScale) private var textScale
    private var viewSpacing: CGFloat { scaledSpacing(2, scaleFactor: textScale) }
    /// "38" approximates the previous 300pt width with whole layout steps.
    private var minWidth: CGFloat { layoutStep(38, scaleFactor: textScale) }
    private var minHeight: CGFloat { layoutStep(25, scaleFactor: textScale) }

    var body: some View {
        VStack(alignment: .leading, spacing: viewSpacing) {
            Text("Внешний вид")
                .font(.headline)
                .applyTextScale()

            Toggle("Отключить анимации при запуске", isOn: $settings.disableLaunchAnimations)
                .applyTextScale()

            Toggle("Отключить все анимации", isOn: $settings.disableAllAnimations)
                .applyTextScale()

            Picker("Размер текста", selection: $settings.textScale) {
                ForEach(scaleOptions, id: \.self) { value in
                    Text("\(Int(value * 100))%")
                        .tag(value)
                }
            }
            .pickerStyle(.menu)
            .labelsHidden()
            .applyTextScale()
            .fixedSize()

            Spacer()
        }
        .scaledPadding()
        .frame(minWidth: minWidth, minHeight: minHeight)
    }
}
#endif
