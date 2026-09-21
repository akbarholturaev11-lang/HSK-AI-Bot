import Foundation

struct IOSSocialAPI: Sendable {
    let client: APIClient
    let authSession: AuthSession

    func rating(timezoneOffsetMinutes: Int = TimeZone.current.secondsFromGMT() / 60) async throws -> IOSRatingResponse {
        let token = try await authSession.bearerToken()
        let offset = min(840, max(-720, timezoneOffsetMinutes))
        return try await client.get(
            "/api/v3/ios/rating/leaderboard",
            bearerToken: token,
            queryItems: [URLQueryItem(name: "tz", value: String(offset))]
        )
    }
}
