#if canImport(SwiftUI)
import SwiftUI

struct ProgressSharePreview: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject
    var shareAction: (_ circleSize: CGFloat, _ ringWidth: CGFloat, _ percentFont: CGFloat, _ titleFont: CGFloat, _ spacing: CGFloat) -> Void

    @State private var circleSize: CGFloat = CGFloat(defaultShareCircleSize)
    @State private var ringWidth: CGFloat = CGFloat(defaultShareRingWidth)
    @State private var percentSize: CGFloat = CGFloat(defaultSharePercentSize)
    @State private var titleSize: CGFloat = CGFloat(defaultShareTitleSize)
    @State private var spacing: CGFloat = CGFloat(defaultShareSpacing)
    @State private var initialized = false

    var body: some View {
        VStack(spacing: scaledSpacing(2)) {
            Spacer()
            ProgressShareView(project: project,
                               circleSize: circleSize,
                               ringWidth: ringWidth,
                               percentFontSize: percentSize,
                               titleFontSize: titleSize,
                               titleSpacing: spacing)
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
                HStack {
                    Text(settings.localized("share_preview_spacing"))
                    Slider(value: $spacing, in: 0...layoutStep(20))
                }
            }
            Spacer()
            HStack(spacing: scaledSpacing(2)) {
                Button("cancel", role: .cancel) { dismiss() }
                Button(settings.localized("share")) {
                    dismiss()
                    DispatchQueue.main.async {
                        shareAction(circleSize, ringWidth, percentSize, titleSize, spacing)
                    }
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(minWidth: shareImageSize + layoutStep(4),
               minHeight: shareImageSize + layoutStep(20))
        .onAppear {
            if !initialized {
                circleSize = CGFloat(settings.lastShareCircleSize)
                ringWidth = CGFloat(settings.lastShareRingWidth)
                percentSize = CGFloat(settings.lastSharePercentSize)
                titleSize = CGFloat(settings.lastShareTitleSize)
                spacing = CGFloat(settings.lastShareSpacing)
                initialized = true
            }
        }
    }
}
#endif
