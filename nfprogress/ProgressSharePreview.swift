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

    private var orientationScale: CGFloat {
#if os(iOS)
        if UIDevice.current.userInterfaceIdiom == .phone {
            return showingFullImage ? 1 : 0.5
        } else {
            return containerSize.width > containerSize.height ? 0.75 : 1
        }
#else
        return 1
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
                                   titleSpacing: spacing)
                    .scaleEffect(orientationScale)
                    .onTapGesture {
#if os(iOS)
                        if orientationScale < 1 { showingFullImage = true }
#endif
                    }
                VStack(spacing: scaledSpacing(0.5)) {
                    pickerRow(title: settings.localized("share_preview_circle_size"), value: $circlePercent)
                    pickerRow(title: settings.localized("share_preview_ring_width"), value: $ringPercent)
                    pickerRow(title: settings.localized("share_preview_percent_size"), value: $percentFontPercent)
                    pickerRow(title: settings.localized("share_preview_title_size"), value: $titleFontPercent)
                    pickerRow(title: settings.localized("share_preview_spacing"), value: $spacingPercent)
                }
                Spacer()
            }
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
            ToolbarItemGroup(placement: .bottomBar) { bottomControls }
        }
        #else
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .safeAreaInset(edge: .bottom) { bottomControls }
        #endif
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
            VStack {
                HStack {
                    Button(settings.localized("cancel")) { showingFullImage = false }
                        .padding()
                    Spacer()
                }
                ProgressShareView(project: project,
                                   circleSize: circleSize,
                                   ringWidth: ringWidth,
                                   percentFontSize: percentSize,
                                   titleFontSize: titleSize,
                                   titleSpacing: spacing)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color.white)
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
