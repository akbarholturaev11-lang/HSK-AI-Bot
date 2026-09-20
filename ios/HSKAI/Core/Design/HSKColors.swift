import SwiftUI
import UIKit

enum HSKColors {
    static let paper = dynamic(light: 0xF6F8FB, dark: 0x07131D)
    static let paperRaised = dynamic(light: 0xFFFFFF, dark: 0x0D2130)
    static let ink = dynamic(light: 0x17212B, dark: 0xF5FAFD)
    static let inkSecondary = dynamic(light: 0x607080, dark: 0xAAC0CF)
    static let divider = dynamic(light: 0xDDE5EC, dark: 0x244456)

    static let cinnabar = dynamic(light: 0xE84C45, dark: 0x5ED5FF)
    static let cinnabarDark = dynamic(light: 0xB93531, dark: 0x27B6E8)
    static let cinnabarSoft = dynamic(light: 0xFFE8E4, dark: 0x0B3B50)

    static let jade = dynamic(light: 0x2C9D6C, dark: 0x58E2A6)
    static let flame = dynamic(light: 0xE98C2F, dark: 0xFF9A63)

    static let glassStroke = Color.white.opacity(0.58)
    static let glassStrokeDark = Color.white.opacity(0.14)
    static let glassHighlight = Color.white.opacity(0.72)
    static let glassShadow = Color.black.opacity(0.14)

    static let auroraBlue = dynamic(light: 0xB9E7FF, dark: 0x0B5270)
    static let auroraMint = dynamic(light: 0xC7F2DF, dark: 0x0C5A48)
    static let auroraRose = dynamic(light: 0xFFD2D7, dark: 0x6E2835)

    private static func dynamic(light: UInt32, dark: UInt32) -> Color {
        Color(
            uiColor: UIColor { traits in
                UIColor(rgb: traits.userInterfaceStyle == .dark ? dark : light)
            }
        )
    }
}

private extension UIColor {
    convenience init(rgb: UInt32) {
        self.init(
            red: CGFloat((rgb >> 16) & 0xFF) / 255,
            green: CGFloat((rgb >> 8) & 0xFF) / 255,
            blue: CGFloat(rgb & 0xFF) / 255,
            alpha: 1
        )
    }
}
