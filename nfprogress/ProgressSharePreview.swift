#if canImport(SwiftUI)
import SwiftUI
#if canImport(AppKit)
import AppKit
#endif

struct ProgressSharePreview: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    var project: WritingProject

    // Значения хранятся как проценты от базовых (1...100)
    @State private var circlePercent: Double = 100
    @State private var ringPercent: Double = 100
    @State private var percentFontPercent: Double = 100
    @State private var titleFontPercent: Double = 100
    @State private var spacingPercent: Double = 100
    @State private var offsetPercent: Double = 0
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
    private var titleOffset: CGFloat {
        CGFloat(offsetPercent) / 100 * (shareImageSize / 4)
    }

    private var orientationScale: CGFloat {
#if os(iOS)
        if isPhone {
            return showingFullImage ? 2 : 1
        } else {
            return (containerSize.width > containerSize.height ? 1.5 : 2)
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
                                   circleSize: circleSize,
                                   ringWidth: ringWidth,
                                   percentFontSize: percentSize,
                                   titleFontSize: titleSize,
                                   titleSpacing: spacing,
                                   titleOffset: titleOffset)
                    .scaleEffect(orientationScale)
                    .frame(width: shareImageSize * orientationScale,
                           height: shareImageSize * orientationScale)
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
                    controlRow(title: settings.localized("share_preview_title_offset"), value: $offsetPercent, range: -100...100)
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
        .toolbar {
            ToolbarItemGroup { bottomControls }
        }
        #else
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .safeAreaInset(edge: .bottom) { bottomControls }
        #endif
        .onAppear {
            if !initialized {
                circlePercent = max(1, min(100, settings.lastShareCircleSize / defaultShareCircleSize * 100))
                ringPercent = max(1, min(100, settings.lastShareRingWidth / defaultShareRingWidth * 100))
                percentFontPercent = max(1, min(100, settings.lastSharePercentSize / defaultSharePercentSize * 100))
                titleFontPercent = max(1, min(100, settings.lastShareTitleSize / defaultShareTitleSize * 100))
                spacingPercent = max(1, min(100, settings.lastShareSpacing / defaultShareSpacing * 100))
                offsetPercent = max(-100, min(100, settings.lastShareTitleOffset / (shareImageSize / 4) * 100))
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
                                                  titleSpacing: spacing,
                                                  titleOffset: titleOffset) {
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
                                         titleSpacing: spacing,
                                         titleOffset: titleOffset) else { return }
        settings.lastShareCircleSize = Double(circleSize)
        settings.lastShareRingWidth = Double(ringWidth)
        settings.lastSharePercentSize = Double(percentSize)
        settings.lastShareTitleSize = Double(titleSize)
        settings.lastShareSpacing = Double(spacing)
        settings.lastShareTitleOffset = Double(titleOffset)
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
    private func sliderRow(title: String, value: Binding<Double>, range: ClosedRange<Double>) -> some View {
        HStack {
            Text(title)
                .font(.footnote)
            Slider(value: value, in: range)
        }
    }

    @ViewBuilder
    private func pickerRow(title: String, value: Binding<Double>, range: ClosedRange<Double>) -> some View {
        HStack {
            Text(title)
                .font(.footnote)
            Picker("", selection: Binding(
                get: { Int(value.wrappedValue.rounded()) },
                set: { value.wrappedValue = Double($0) }
            )) {
                ForEach(Int(range.lowerBound)...Int(range.upperBound), id: \.self) { num in
                    Text("\(num)").tag(num)
                }
            }
            .labelsHidden()
            .pickerStyle(.menu)
        }
    }

    @ViewBuilder
    private func controlRow(title: String, value: Binding<Double>, range: ClosedRange<Double> = 1...100) -> some View {
#if os(iOS)
        if isPhone {
            pickerRow(title: title, value: value, range: range)
        } else {
            sliderRow(title: title, value: value, range: range)
        }
#else
        sliderRow(title: title, value: value, range: range)
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
