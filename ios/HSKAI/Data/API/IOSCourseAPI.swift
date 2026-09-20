import Foundation

struct IOSCourseAPI: Sendable {
    let client: APIClient
    let authSession: AuthSession

    func courseMap() async throws -> IOSCourseMap {
        let token = try await authSession.bearerToken()
        let rawOffset = TimeZone.current.secondsFromGMT() / 60
        let offset = min(840, max(-720, rawOffset))
        return try await client.get(
            "/api/v3/ios/course/map",
            bearerToken: token,
            queryItems: [URLQueryItem(name: "tz", value: String(offset))]
        )
    }

    func onboardingStatus() async throws -> IOSOnboardingStatus {
        let token = try await authSession.bearerToken()
        return try await client.get(
            "/api/v3/ios/course/onboarding",
            bearerToken: token
        )
    }

    func completeOnboarding(
        level: String,
        goal: String,
        language: String,
        timezoneOffsetMinutes: Int
    ) async throws -> IOSOnboardingComplete {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/course/onboarding",
            body: IOSOnboardingRequest(
                level: level,
                goal: goal,
                dailyMinutes: 10,
                startMode: "lesson_1",
                language: language,
                timezoneOffsetMinutes: timezoneOffsetMinutes,
                activationVariant: "direct_start_v1"
            ),
            bearerToken: token
        )
    }
}
