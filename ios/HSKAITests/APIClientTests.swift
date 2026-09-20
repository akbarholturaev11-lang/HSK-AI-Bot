import XCTest
@testable import HSKAI

final class APIClientTests: XCTestCase {
    func testProductionOriginUsesHTTPS() {
        XCTAssertEqual(AppEnvironment.production.apiBaseURL.scheme, "https")
    }

    func testRequestStaysOnConfiguredOrigin() throws {
        let environment = AppEnvironment(
            apiBaseURL: URL(string: "https://example.com")!
        )
        let client = APIClient(environment: environment)

        let request = try client.makeRequest(
            path: "/api/v3/test",
            method: "GET",
            queryItems: [URLQueryItem(name: "q", value: "你")]
        )

        XCTAssertEqual(request.url?.host, "example.com")
        XCTAssertEqual(request.url?.scheme, "https")
        XCTAssertEqual(request.url?.path, "/api/v3/test")
    }

    func testAbsoluteURLIsRejected() {
        let client = APIClient(environment: .production)

        XCTAssertThrowsError(
            try client.makeRequest(
                path: "https://evil.example/api",
                method: "GET"
            )
        ) { error in
            XCTAssertEqual(error as? APIError, .invalidPath)
        }
    }
}


final class AuthModelTests: XCTestCase {
    func testAccessTokenRefreshesEarly() {
        let now = Date(timeIntervalSince1970: 1_000)
        let token = AccessToken(
            value: "token",
            expiresAt: now.addingTimeInterval(20)
        )

        XCTAssertFalse(token.isUsable(at: now))
    }

    func testAccessTokenIsUsableOutsideRefreshSkew() {
        let now = Date(timeIntervalSince1970: 1_000)
        let token = AccessToken(
            value: "token",
            expiresAt: now.addingTimeInterval(120)
        )

        XCTAssertTrue(token.isUsable(at: now))
    }
}
