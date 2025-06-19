import SwiftUI

struct SettingsView: View {
    @AppStorage("disableLaunchAnimations") private var launchAnimations = false
    @AppStorage("disableAllAnimations") private var allAnimations = false
    @AppStorage("textScale") private var scale: Double = 1.0
    private let scaleOptions: [Double] = Array(stride(from: 1.0, through: 3.0, by: 0.1))

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Внешний вид")
                .font(.headline)
                .applyTextScale()

            Toggle("Отключить анимации при запуске", isOn: $launchAnimations)
                .applyTextScale()

            Toggle("Отключить все анимации", isOn: $allAnimations)
                .applyTextScale()

            Picker("Размер текста", selection: $scale) {
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
