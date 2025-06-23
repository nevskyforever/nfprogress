#if canImport(SwiftUI)
import SwiftUI

#if canImport(UIKit)
import UIKit
public typealias OSImage = UIImage
#elseif canImport(AppKit)
import AppKit
public typealias OSImage = NSImage
#endif

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
                .frame(width: layoutStep(20), height: layoutStep(20))
            Text(project.title)
                .font(.title2.bold())
        }
        .padding()
        .background(Color.white)
    }
}

@MainActor
func progressShareImage(for project: WritingProject) -> OSImage? {
    // Break the rendering steps into smaller expressions to
    // help the compiler with type inference.
    let view = ProgressShareView(project: project)
    let renderer = ImageRenderer(content: view)
#if canImport(UIKit)
    renderer.scale = UIScreen.main.scale
    return renderer.uiImage
#else
    renderer.scale = NSScreen.main?.backingScaleFactor ?? 2
    return renderer.nsImage
#endif
}

struct ShareableProgressImage: Transferable {
    var image: OSImage

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(contentType: .png) { item in
#if canImport(UIKit)
            item.image.pngData() ?? Data()
#else
            guard let tiff = item.image.tiffRepresentation,
                  let rep = NSBitmapImageRep(data: tiff),
                  let data = rep.representation(using: .png, properties: [:]) else {
                return Data()
            }
            return data
#endif
        } importing: { data in
#if canImport(UIKit)
            ShareableProgressImage(image: UIImage(data: data) ?? UIImage())
#else
            ShareableProgressImage(image: NSImage(data: data) ?? NSImage())
#endif
        }
    }
}
#endif
