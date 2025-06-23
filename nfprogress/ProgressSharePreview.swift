#if canImport(SwiftUI)
import SwiftUI
#if canImport(AppKit)
import AppKit
#endif

struct ProgressSharePreview: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject

    @State private var circleSize: CGFloat = CGFloat(defaultShareCircleSize)
    @State private var ringWidth: CGFloat = CGFloat(defaultShareRingWidth)
    @State private var percentSize: CGFloat = CGFloat(defaultSharePercentSize)
    @State private var titleSize: CGFloat = CGFloat(defaultShareTitleSize)
    @State private var spacing: CGFloat = CGFloat(defaultShareSpacing)
    @State private var initialized = false
#if os(iOS)
    @State private var shareURL: URL?
    @State private var showingShareSheet = false
#endif

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
                Button(settings.localized("share")) { shareProgress() }
                    .buttonStyle(.borderedProminent)
                    .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(width: 560, height: 730)
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
#if os(iOS)
        .sheet(isPresented: $showingShareSheet, onDismiss: {
            if let url = shareURL { try? FileManager.default.removeItem(at: url) }
            shareURL = nil
            dismiss()
        }) {
            if let url = shareURL {
                ShareSheet(items: [url])
            }
        }
#endif
    }

    private func shareProgress() {
        guard let url = progressShareURL(for: project,
                                         circleSize: circleSize,
                                         ringWidth: ringWidth,
                                         percentFontSize: percentSize,
                                         titleFontSize: titleSize,
                                         titleSpacing: spacing) else { return }
        settings.lastShareCircleSize = Double(circleSize)
        settings.lastShareRingWidth = Double(ringWidth)
        settings.lastSharePercentSize = Double(percentSize)
        settings.lastShareTitleSize = Double(titleSize)
        settings.lastShareSpacing = Double(spacing)
#if os(iOS)
        shareURL = url
        showingShareSheet = true
#else
        let picker = NSSharingServicePicker(items: [url])
        if let window = NSApp.keyWindow ?? NSApp.windows.first {
            picker.show(relativeTo: .zero, of: window.contentView!, preferredEdge: .minY)
        }
        dismiss()
#endif
    }
}
#endif
