import XCTest
@testable import HSKAI

final class DeepLinkRouterTests: XCTestCase {
    func testRoutesSupportedTabs() {
        XCTAssertEqual(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://course")!), .course)
        XCTAssertEqual(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://practice")!), .practice)
        XCTAssertEqual(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://dictionary")!), .dictionary)
        XCTAssertEqual(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://rating")!), .rating)
        XCTAssertEqual(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://profile")!), .profile)
    }

    func testRejectsUnknownSchemeAndDestination() {
        XCTAssertNil(IOSDeepLinkRouter.destination(for: URL(string: "https://example.com/practice")!))
        XCTAssertNil(IOSDeepLinkRouter.destination(for: URL(string: "pomp-hsk-ai://unknown")!))
    }
}
