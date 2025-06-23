#if canImport(SwiftUI)
import SwiftUI

#if canImport(UIKit)
import UIKit
public typealias OSImage = UIImage
#elseif canImport(AppKit)
import AppKit
public typealias OSImage = NSImage
#endif

/// Size of the exported progress image in points.
let shareImageSize: CGFloat = 500

/// Reads the size of the view and writes it into the provided binding.
private struct SizeReader: View {
    @Binding var size: CGSize
    var body: some View {
        GeometryReader { geo in
            Color.clear
                .preference(key: SizePreferenceKey.self, value: geo.size)
        }
        .onPreferenceChange(SizePreferenceKey.self) { size = $0 }
    }
}

private struct SizePreferenceKey: PreferenceKey {
    static var defaultValue: CGSize = .zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}

/// Snapshot of ``ProgressCircleView`` without animations.
private struct ProgressCircleSnapshotView: View {
    var project: WritingProject
    var size: CGFloat
    var ringWidth: CGFloat
    var percentFontSize: CGFloat

    private var progress: Double {
        guard project.goal > 0 else { return 0 }
        let value = Double(project.currentProgress) / Double(project.goal)
        return min(max(value, 0), 1)
    }

    private var color: Color { .interpolate(from: .red, to: .green, fraction: progress) }

    var body: some View {
        ZStack {
            Circle().stroke(Color.gray.opacity(0.3), lineWidth: ringWidth)
            Circle()
                .trim(from: 0, to: CGFloat(progress))
                .stroke(color, style: StrokeStyle(lineWidth: ringWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
            let percent = Int(ceil(progress * 100))
            Text("\(percent)%")
                .font(.system(size: percentFontSize))
                .monospacedDigit()
                .bold()
                .foregroundColor(color)
        }
        .frame(width: size, height: size)
    }
}

struct ProgressShareView: View {
    var project: WritingProject
    var circleSize: CGFloat = shareImageSize * 0.35
    var ringWidth: CGFloat = layoutStep(3)
    var percentFontSize: CGFloat = calcFontSize(token: .progressValueLarge) * 1.5
    var titleFontSize: CGFloat = 56

    @State private var titleSize: CGSize = .zero

    /// Final scale ensuring both title and circle fit into the square canvas.
    private var circleScale: CGFloat {
        let available = shareImageSize - titleSize.height - scaledSpacing(2)
        return min(1, max(0.1, available / circleSize))
    }

    var body: some View {
        VStack(spacing: scaledSpacing(2)) {
            ProgressCircleSnapshotView(project: project,
                                       size: circleSize,
                                       ringWidth: ringWidth,
                                       percentFontSize: percentFontSize)
                .scaleEffect(circleScale)
            Spacer()
            Text(project.title)
                .font(.system(size: titleFontSize, weight: .bold))
                .multilineTextAlignment(.center)
                .lineLimit(nil)
                .fixedSize(horizontal: false, vertical: true)
                .background(SizeReader(size: $titleSize))
                .padding(.bottom, scaledSpacing(1))
        }
        .frame(width: shareImageSize, height: shareImageSize, alignment: .bottom)
        .background(Color.white)
    }
}

@MainActor
func progressShareImage(for project: WritingProject,
                        circleSize: CGFloat = shareImageSize * 0.35,
                        ringWidth: CGFloat = layoutStep(3),
                        percentFontSize: CGFloat = calcFontSize(token: .progressValueLarge) * 1.5,
                        titleFontSize: CGFloat = 56) -> OSImage? {
    let view = ProgressShareView(project: project,
                                 circleSize: circleSize,
                                 ringWidth: ringWidth,
                                 percentFontSize: percentFontSize,
                                 titleFontSize: titleFontSize)
    let renderer = ImageRenderer(content: view)
#if swift(>=5.9)
    renderer.proposedSize = ProposedViewSize(width: shareImageSize, height: shareImageSize)
#else
    renderer.proposedSize = CGSize(width: shareImageSize, height: shareImageSize)
#endif
#if canImport(UIKit)
    renderer.scale = UIScreen.main.scale
    return renderer.uiImage
#else
    renderer.scale = NSScreen.main?.backingScaleFactor ?? 2
    return renderer.nsImage
#endif
}


@MainActor
func progressShareURL(for project: WritingProject,
                      circleSize: CGFloat = shareImageSize * 0.35,
                      ringWidth: CGFloat = layoutStep(3),
                      percentFontSize: CGFloat = calcFontSize(token: .progressValueLarge) * 1.5,
                      titleFontSize: CGFloat = 56) -> URL? {
    guard let image = progressShareImage(for: project,
                                         circleSize: circleSize,
                                         ringWidth: ringWidth,
                                         percentFontSize: percentFontSize,
                                         titleFontSize: titleFontSize) else { return nil }
#if canImport(UIKit)
    guard let data = image.pngData() else { return nil }
#else
    guard let tiff = image.tiffRepresentation,
          let rep = NSBitmapImageRep(data: tiff),
          let data = rep.representation(using: .png, properties: [:]) else {
        return nil
    }
#endif
    let url = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString + ".png")
    do {
        try data.write(to: url)
        return url
    } catch {
        print("Ошибка сохранения PNG: \(error)")
        return nil
    }
}
#endif
