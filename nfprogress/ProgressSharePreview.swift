#if canImport(SwiftUI)
import SwiftUI
#if canImport(AppKit)
import AppKit
#endif

struct ProgressSharePreview: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject

    // Values stored as percentages of defaults (1...100)
    @State private var circlePercent: Int = 100
    @State private var ringPercent: Int = 100
    @State private var percentFontPercent: Int = 100
    @State private var titleFontPercent: Int = 100
    @State private var spacingPercent: Int = 100
    @State private var initialized = false
#if os(iOS)
    @State private var shareURL: URL?
    @State private var showingShareSheet = false
    @State private var showingFullImage = false
    private var isPhone: Bool { UIDevice.current.userInterfaceIdiom == .phone }
#endif
#if os(iOS)
    @State private var containerSize: CGSize = .zero
#endif

    private var circleSize: CGFloat {
        CGFloat(circlePercent) / 100 * CGFloat(defaultShareCircleSize)
    }
    private var ringWidth: CGFloat {
        CGFloat(ringPercent) / 100 * CGFloat(defaultShareRingWidth)
    }
    private var percentSize: CGFloat {
        CGFloat(percentFontPercent) / 100 * CGFloat(defaultSharePercentSize)
    }
    private var titleSize: CGFloat {
        CGFloat(titleFontPercent) / 100 * CGFloat(defaultShareTitleSize)
    }
    private var spacing: CGFloat {
        CGFloat(spacingPercent) / 100 * CGFloat(defaultShareSpacing)
    }

    private var previewScale: CGFloat {
#if os(iOS)
        if isPhone {
            return showingFullImage ? 2 : 1
        } else {
            return containerSize.width > containerSize.height ? 1.5 : 2
        }
#else
        return 2
#endif
    }

    var body: some View {
        GeometryReader { geo in
            VStack(spacing: scaledSpacing(1.5)) {
                Spacer()
                ProgressShareView(project: project,
                                   circleSize: circleSize * previewScale,
                                   ringWidth: ringWidth * previewScale,
                                   percentFontSize: percentSize * previewScale,
                                   titleFontSize: titleSize * previewScale,
                                   titleSpacing: spacing * previewScale)
                    .frame(width: shareImageSize * previewScale,
                           height: shareImageSize * previewScale)
                    .onTapGesture {
#if os(iOS)
                        if !showingFullImage { showingFullImage = true }
#endif
                    }
                VStack(spacing: scaledSpacing(0.5)) {
                    controlRow(title: settings.localized("share_preview_circle_size"), value: $circlePercent)
                    controlRow(title: settings.localized("share_preview_ring_width"), value: $ringPercent)
                    controlRow(title: settings.localized("share_preview_percent_size"), value: $percentFontPercent)
                    controlRow(title: settings.localized("share_preview_title_size"), value: $titleFontPercent)
                    controlRow(title: settings.localized("share_preview_spacing"), value: $spacingPercent)
                }
                Spacer()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .onChange(of: geo.size) { newValue in
#if os(iOS)
                containerSize = newValue
#endif
            }
        }
        .scaledPadding()
        #if os(macOS)
        .frame(width: 560, height: 730)
        #else
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        #endif
        .safeAreaInset(edge: .bottom) { bottomControls }
        .onAppear {
            if !initialized {
                circlePercent = max(1, min(100, Int((settings.lastShareCircleSize / defaultShareCircleSize * 100).rounded())))
                ringPercent = max(1, min(100, Int((settings.lastShareRingWidth / defaultShareRingWidth * 100).rounded())))
                percentFontPercent = max(1, min(100, Int((settings.lastSharePercentSize / defaultSharePercentSize * 100).rounded())))
                titleFontPercent = max(1, min(100, Int((settings.lastShareTitleSize / defaultShareTitleSize * 100).rounded())))
                spacingPercent = max(1, min(100, Int((settings.lastShareSpacing / defaultShareSpacing * 100).rounded())))
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
        .fullScreenCover(isPresented: $showingFullImage) {
            ZStack {
                Color.gray.opacity(0.3).ignoresSafeArea()
                VStack {
                    Spacer()
                    if let img = progressShareImage(for: project,
                                                  circleSize: circleSize,
                                                  ringWidth: ringWidth,
                                                  percentFontSize: percentSize,
                                                  titleFontSize: titleSize,
                                                  titleSpacing: spacing) {
#if os(iOS)
                        Image(uiImage: img)
#else
                        Image(nsImage: img)
#endif
                            .resizable()
                            .interpolation(.high)
                            .scaledToFit()
                    }
                    Spacer()
                }
                VStack {
                    HStack {
                        Button(settings.localized("cancel")) { showingFullImage = false }
                            .padding()
                        Spacer()
                    }
                    Spacer()
                }
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

    @ViewBuilder
    private func sliderRow(title: String, value: Binding<Int>) -> some View {
        HStack {
            Text(title)
                .font(.footnote)
            Slider(value: Binding(
                get: { Double(value.wrappedValue) },
                set: { value.wrappedValue = Int($0) }
            ), in: 1...100, step: 1)
        }
    }

    @ViewBuilder
    private func pickerRow(title: String, value: Binding<Int>) -> some View {
        HStack {
            Text(title)
                .font(.footnote)
            Picker("", selection: value) {
                ForEach(1..<101) { num in
                    Text("\(num)").tag(num)
                }
            }
            .labelsHidden()
            .pickerStyle(.menu)
        }
    }

    @ViewBuilder
    private func controlRow(title: String, value: Binding<Int>) -> some View {
#if os(iOS)
        if isPhone {
            pickerRow(title: title, value: value)
        } else {
            sliderRow(title: title, value: value)
        }
#else
        sliderRow(title: title, value: value)
#endif
    }

    @ViewBuilder
    private var bottomControls: some View {
        HStack {
            Button(settings.localized("cancel"), role: .cancel) { dismiss() }
            Spacer()
            Button(settings.localized("share")) { shareProgress() }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
        }
        .scaledPadding()
    }
}
#endif
