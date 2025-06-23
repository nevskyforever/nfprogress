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
private let shareImageSize: CGFloat = 500

/// Snapshot of ``ProgressCircleView`` without animations.
private struct ProgressCircleSnapshotView: View {
    var project: WritingProject
    var style: ProgressCircleStyle = .large

    private var progress: Double {
        guard project.goal > 0 else { return 0 }
        let value = Double(project.currentProgress) / Double(project.goal)
        return min(max(value, 0), 1)
    }

    private var ringWidth: CGFloat { style == .large ? layoutStep(3) : layoutStep(2) }
    private var color: Color { .interpolate(from: .red, to: .green, fraction: progress) }
    private var fontToken: FontToken { style == .large ? .progressValueLarge : .progressValue }

    var body: some View {
        ZStack {
            Circle().stroke(Color.gray.opacity(0.3), lineWidth: ringWidth)
            Circle()
                .trim(from: 0, to: CGFloat(progress))
                .stroke(color, style: StrokeStyle(lineWidth: ringWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
            let percent = Int(ceil(progress * 100))
            Text("\(percent)%")
                .scaledFont(fontToken)
                .monospacedDigit()
                .bold()
                .foregroundColor(color)
        }
    }
}

private struct ProgressShareView: View {
    var project: WritingProject

    var body: some View {
        VStack(spacing: scaledSpacing(2)) {
            ProgressCircleSnapshotView(project: project, style: .large)
                .frame(width: shareImageSize * 0.7, height: shareImageSize * 0.7)
            Text(project.title)
                .font(.title.bold())
                .multilineTextAlignment(.center)
        }
        .frame(width: shareImageSize, height: shareImageSize)
        .background(Color.white)
    }
}

@MainActor
func progressShareImage(for project: WritingProject) -> OSImage? {
    let view = ProgressShareView(project: project)
    let renderer = ImageRenderer(content: view)
    renderer.proposedSize = ProposedViewSize(width: shareImageSize, height: shareImageSize)
#if canImport(UIKit)
    renderer.scale = UIScreen.main.scale
    return renderer.uiImage
#else
    renderer.scale = NSScreen.main?.backingScaleFactor ?? 2
    return renderer.nsImage
#endif
}


@MainActor
func progressShareURL(for project: WritingProject) -> URL? {
    guard let image = progressShareImage(for: project) else { return nil }
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
