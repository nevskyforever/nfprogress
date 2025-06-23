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

/// Default parameters for share image preview.
let defaultShareCircleSize: CGFloat = shareImageSize * 0.35
let defaultShareRingWidth: CGFloat = layoutStep(3)
let defaultSharePercentSize: CGFloat = CGFloat(calcFontSize(token: .progressValueLarge) * 1.5)
let defaultShareTitleSize: CGFloat = 56
let defaultShareSpacing: CGFloat = scaledSpacing(2)

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
    var circleSize: CGFloat = defaultShareCircleSize
    var ringWidth: CGFloat = defaultShareRingWidth
    var percentFontSize: CGFloat = defaultSharePercentSize
    var titleFontSize: CGFloat = defaultShareTitleSize
    var titleSpacing: CGFloat = defaultShareSpacing

    var body: some View {
        VStack(spacing: 0) {
            Spacer()
            ProgressCircleSnapshotView(project: project,
                                       size: circleSize,
                                       ringWidth: ringWidth,
                                       percentFontSize: percentFontSize)
            Spacer().frame(height: titleSpacing)
            Text(project.title)
                .font(.system(size: titleFontSize, weight: .bold))
                .multilineTextAlignment(.center)
                .lineLimit(nil)
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
        }
        .frame(width: shareImageSize, height: shareImageSize)
        .background(Color.white)
    }
}

@MainActor
func progressShareImage(for project: WritingProject,
                        circleSize: CGFloat = defaultShareCircleSize,
                        ringWidth: CGFloat = defaultShareRingWidth,
                        percentFontSize: CGFloat = defaultSharePercentSize,
                        titleFontSize: CGFloat = defaultShareTitleSize,
                        titleSpacing: CGFloat = defaultShareSpacing) -> OSImage? {
    let view = ProgressShareView(project: project,
                                 circleSize: circleSize,
                                 ringWidth: ringWidth,
                                 percentFontSize: percentFontSize,
                                 titleFontSize: titleFontSize,
                                 titleSpacing: titleSpacing)
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
                      circleSize: CGFloat = defaultShareCircleSize,
                      ringWidth: CGFloat = defaultShareRingWidth,
                      percentFontSize: CGFloat = defaultSharePercentSize,
                      titleFontSize: CGFloat = defaultShareTitleSize,
                      titleSpacing: CGFloat = defaultShareSpacing) -> URL? {
    guard let image = progressShareImage(for: project,
                                         circleSize: circleSize,
                                         ringWidth: ringWidth,
                                         percentFontSize: percentFontSize,
                                         titleFontSize: titleFontSize,
                                         titleSpacing: titleSpacing) else { return nil }
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
