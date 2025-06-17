import SwiftUI

struct AdaptiveImportExportButtons: View {
  var hasSelection: Bool
  var exportAction: () -> Void
  var importAction: () -> Void

  var body: some View {
    ViewThatFits(in: .horizontal) {
      HStack(spacing: 8) {
        if hasSelection {
          Button("Экспортировать", action: exportAction)
        }
        Button("Импортировать", action: importAction)
      }
      .layoutPriority(1)
      HStack(spacing: 8) {
        if hasSelection {
          Button(action: exportAction) {
            Image(systemName: "square.and.arrow.up")
          }
          .help("Export")
        }
        Button(action: importAction) {
          Image(systemName: "square.and.arrow.down")
        }
        .help("Import")
      }
    }
    .animation(.default, value: hasSelection)
  }
}

#Preview {
  AdaptiveImportExportButtons(hasSelection: true, exportAction: {}, importAction: {})
}
