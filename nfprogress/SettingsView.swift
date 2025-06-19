import SwiftUI

struct SettingsView: View {
    @State private var launchAnimations = AppSettings.disableLaunchAnimations
    @State private var allAnimations = AppSettings.disableAllAnimations
    @State private var scale = AppSettings.textScale
    @State private var pendingAction: (() -> Void)?
    @State private var showRestart = false

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Внешний вид")
                .font(.headline)
                .applyTextScale()

            Toggle("Отключить анимации при запуске", isOn: $launchAnimations)
                .onChange(of: launchAnimations) { newValue in
                    pendingAction = { AppSettings.disableLaunchAnimations = newValue }
                    showRestart = true
                }
                .applyTextScale()

            Toggle("Отключить все анимации", isOn: $allAnimations)
                .onChange(of: allAnimations) { newValue in
                    pendingAction = { AppSettings.disableAllAnimations = newValue }
                    showRestart = true
                }
                .applyTextScale()

            HStack {
                Text("Размер текста: \(Int(scale * 100))%")
                    .applyTextScale()
                Slider(value: $scale, in: 1...3, step: 0.1, onEditingChanged: { editing in
                    if !editing {
                        pendingAction = { AppSettings.textScale = scale }
                        showRestart = true
                    }
                })
            }

            Spacer()
        }
        .padding()
        .frame(minWidth: 300, minHeight: 200)
        .alert("Требуется перезапуск", isPresented: $showRestart) {
            Button("Перезапустить") {
                pendingAction?()
                pendingAction = nil
                #if os(macOS)
                restartApp()
                #endif
            }
            Button("Позже", role: .cancel) {
                revert()
            }
        } message: {
            Text("Чтобы изменения вступили в силу, необходимо перезапустить приложение.")
        }
    }

    private func revert() {
        launchAnimations = AppSettings.disableLaunchAnimations
        allAnimations = AppSettings.disableAllAnimations
        scale = AppSettings.textScale
        pendingAction = nil
    }
}
