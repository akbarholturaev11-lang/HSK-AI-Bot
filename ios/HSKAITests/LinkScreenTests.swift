import XCTest
@testable import HSKAI

final class LinkScreenTests: XCTestCase {
    func testCountdownFormatting() {
        XCTAssertEqual(LinkScreen.formatRemaining(0), "0:00")
        XCTAssertEqual(LinkScreen.formatRemaining(9), "0:09")
        XCTAssertEqual(LinkScreen.formatRemaining(125), "2:05")
        XCTAssertEqual(LinkScreen.formatRemaining(-3), "0:00")
    }
}
