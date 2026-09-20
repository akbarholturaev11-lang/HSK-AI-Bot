import SwiftUI

struct HSKGlassBackdrop: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    HSKColors.paper,
                    colorScheme == .dark
                        ? Color(red: 0.035, green: 0.12, blue: 0.17)
                        : Color(red: 0.93, green: 0.97, blue: 1.0),
                    HSKColors.paper,
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(HSKColors.auroraBlue.opacity(colorScheme == .dark ? 0.38 : 0.62))
                .frame(width: 310, height: 310)
                .blur(radius: 55)
                .offset(x: 150, y: -250)

            Circle()
                .fill(HSKColors.auroraRose.opacity(colorScheme == .dark ? 0.24 : 0.48))
                .frame(width: 270, height: 270)
                .blur(radius: 62)
                .offset(x: -170, y: 90)

            Circle()
                .fill(HSKColors.auroraMint.opacity(colorScheme == .dark ? 0.22 : 0.44))
                .frame(width: 300, height: 300)
                .blur(radius: 68)
                .offset(x: 130, y: 360)

            LinearGradient(
                colors: [
                    Color.white.opacity(colorScheme == .dark ? 0.02 : 0.28),
                    Color.clear,
                ],
                startPoint: .top,
                endPoint: .center
            )
        }
        .ignoresSafeArea()
    }
}

struct HSKGlassCard<Content: View>: View {
    let cornerRadius: CGFloat
    let padding: CGFloat
    let tint: Color?
    @ViewBuilder let content: Content

    init(
        cornerRadius: CGFloat = 24,
        padding: CGFloat = 18,
        tint: Color? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.cornerRadius = cornerRadius
        self.padding = padding
        self.tint = tint
        self.content = content()
    }

    var body: some View {
        content
            .padding(padding)
            .background {
                ZStack {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(.ultraThinMaterial)

                    if let tint {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .fill(tint.opacity(0.11))
                    }

                    LinearGradient(
                        colors: [
                            Color.white.opacity(0.24),
                            Color.white.opacity(0.04),
                            Color.clear,
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                    .clipShape(
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    )
                }
            }
            .overlay {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.66),
                                Color.white.opacity(0.20),
                                HSKColors.divider.opacity(0.46),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 0.9
                    )
            }
            .shadow(color: HSKColors.glassShadow.opacity(0.45), radius: 24, y: 12)
            .shadow(color: Color.white.opacity(0.18), radius: 1, y: -1)
    }
}

struct HSKGlassPill<Content: View>: View {
    @ViewBuilder let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay(
                Capsule()
                    .stroke(Color.white.opacity(0.42), lineWidth: 0.8)
            )
            .shadow(color: Color.black.opacity(0.08), radius: 10, y: 5)
    }
}

struct HSKGlassIconButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .frame(width: 44, height: 44)
            .background(.ultraThinMaterial, in: Circle())
            .overlay(Circle().stroke(Color.white.opacity(0.46), lineWidth: 0.8))
            .shadow(color: Color.black.opacity(0.08), radius: 10, y: 5)
            .scaleEffect(configuration.isPressed ? 0.92 : 1)
            .animation(.spring(response: 0.25, dampingFraction: 0.76), value: configuration.isPressed)
    }
}

struct HSKGlassSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(HSKColors.ink)
            .frame(maxWidth: .infinity)
            .frame(minHeight: 52)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 17, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 17, style: .continuous)
                    .stroke(Color.white.opacity(0.52), lineWidth: 0.9)
            )
            .shadow(color: Color.black.opacity(0.08), radius: 12, y: 6)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .opacity(configuration.isPressed ? 0.88 : 1)
            .animation(.spring(response: 0.24, dampingFraction: 0.78), value: configuration.isPressed)
    }
}
