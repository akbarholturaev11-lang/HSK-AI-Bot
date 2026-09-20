import SwiftUI

struct HSKPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(minHeight: 54)
            .background {
                ZStack {
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .fill(.ultraThinMaterial)

                    LinearGradient(
                        colors: [
                            HSKColors.cinnabar.opacity(0.94),
                            HSKColors.cinnabarDark.opacity(0.86),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                    .clipShape(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                    )

                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.36),
                            Color.clear,
                        ],
                        startPoint: .top,
                        endPoint: .center
                    )
                    .clipShape(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                    )
                }
            }
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(Color.white.opacity(0.38), lineWidth: 0.9)
            }
            .shadow(color: HSKColors.cinnabar.opacity(0.22), radius: 18, y: 9)
            .scaleEffect(configuration.isPressed ? 0.975 : 1)
            .opacity(configuration.isPressed ? 0.88 : 1)
            .animation(.spring(response: 0.24, dampingFraction: 0.76), value: configuration.isPressed)
    }
}
