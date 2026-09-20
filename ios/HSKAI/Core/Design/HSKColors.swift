import SwiftUI
import UIKit

enum HSKColors {
    static let paper = dynamic(light: 0xFDF9F0, dark: 0x002F49)
    static let paperRaised = dynamic(light: 0xFFFFFF, dark: 0x073B55)
    static let ink = dynamic(light: 0x211D17, dark: 0xF5FAFD)
    static let inkSecondary = dynamic(light: 0x665D50, dark: 0xB8CDDA)
    static let divider = dynamic(light: 0xEAE0CC, dark: 0x17617D)
    static let cinnabar = dynamic(light: 0xE04A40, dark: 0x20BCEB)
    static let cinnabarDark = dynamic(light: 0xB23530, dark: 0x1299C4)
    static let cinnabarSoft = dynamic(light: 0xFDEBE7, dark: 0x0B4C66)
    static let jade = dynamic(light: 0x2FA06A, dark: 0x48D99A)
    static let flame = dynamic(light: 0xFF9600, dark: 0xFF6B66)

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
