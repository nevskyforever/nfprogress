import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    private let scaleOptions: [Double] = Array(stride(from: 1.0, through: 3.0, by: 0.1))

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
            .fixedSize()
            .applyTextScale()

            Spacer()
        }
        .padding()
        .frame(minWidth: 300, minHeight: 200)
    }
}
