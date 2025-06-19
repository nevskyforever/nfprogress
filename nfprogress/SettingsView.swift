import SwiftUI

struct SettingsView: View {
    @AppStorage("disableLaunchAnimations") private var launchAnimations = false
    @AppStorage("disableAllAnimations") private var allAnimations = false
    @AppStorage("textScale") private var scale: Double = 1.0

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Внешний вид")
                .font(.headline)
                .applyTextScale()

            Toggle("Отключить анимации при запуске", isOn: $launchAnimations)
                .applyTextScale()

            Toggle("Отключить все анимации", isOn: $allAnimations)
                .applyTextScale()

            HStack {
                Text("Размер текста: \(Int(scale * 100))%")
                    .applyTextScale()
                Slider(value: $scale, in: 1...3, step: 0.1)
            }

            Spacer()
        }
        .padding()
        .frame(minWidth: 300, minHeight: 200)
    }
}
