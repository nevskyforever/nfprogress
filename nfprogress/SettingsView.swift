#if canImport(SwiftUI)
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    private let scaleOptions = TextScale.values

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
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
            .applyTextScale()

            Spacer()
        }
        .padding()
        .frame(minWidth: 300, minHeight: 200)
    }
}
#endif
