#if canImport(SwiftUI)
import SwiftUI

struct ProgressSharePreview: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject
    var shareAction: (_ circleSize: CGFloat, _ ringWidth: CGFloat, _ percentFont: CGFloat, _ titleFont: CGFloat) -> Void

    @State private var circleSize: CGFloat = shareImageSize * 0.35
    @State private var ringWidth: CGFloat = layoutStep(3)
    @State private var percentSize: CGFloat = calcFontSize(token: .progressValueLarge) * 1.5
    @State private var titleSize: CGFloat = 56

    var body: some View {
        VStack(spacing: scaledSpacing(2)) {
            Spacer()
            ProgressShareView(project: project,
                               circleSize: circleSize,
                               ringWidth: ringWidth,
                               percentFontSize: percentSize,
                               titleFontSize: titleSize)
            VStack {
                HStack {
                    Text(settings.localized("share_preview_circle_size"))
                    Slider(value: $circleSize, in: 100...shareImageSize)
                }
                HStack {
                    Text(settings.localized("share_preview_ring_width"))
                    Slider(value: $ringWidth, in: 1...60)
                }
                HStack {
                    Text(settings.localized("share_preview_percent_size"))
                    Slider(value: $percentSize, in: 10...120)
                }
                HStack {
                    Text(settings.localized("share_preview_title_size"))
                    Slider(value: $titleSize, in: 20...100)
                }
            }
            Spacer()
            HStack(spacing: scaledSpacing(2)) {
                Button("cancel", role: .cancel) { dismiss() }
                Button(settings.localized("export")) {
                    dismiss()
                    DispatchQueue.main.async {
                        shareAction(circleSize, ringWidth, percentSize, titleSize)
                    }
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(minWidth: shareImageSize + layoutStep(4),
               minHeight: shareImageSize + layoutStep(20))
    }
}
#endif
