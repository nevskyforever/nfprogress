import SwiftUI

/// Text view that animates numeric changes smoothly.
struct AnimatedCounterText: Animatable, View {
    /// Current value of the counter in percent (0...1).
    var value: Double

    var animatableData: Double {
        get { value }
        set { value = newValue }
    }

    var body: some View {
        let percent = Int(ceil(value * 100))
        Text("\(percent)%")
            .font(.system(size: 20))
            .monospacedDigit()
            .bold()
    }
}
