import XCTest
final class HSKAIUITests: XCTestCase {
    func testAppLaunchesWithoutCrashing() {
        let app = XCUIApplication()
        app.launchArguments += ["-AppleLanguages", "(uz)", "-AppleLocale", "uz_UZ"]
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 8))
    }
}
