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

    func updateStudyPreferences(
        goal: String? = nil,
        dailyMinutes: Int? = nil,
        dailyGoalXp: Int? = nil,
        preferredFocus: String? = nil
    ) async throws -> IOSStudyPreferencesResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/preferences/study",
            body: IOSStudyPreferencesRequest(
                goal: goal,
                dailyMinutes: dailyMinutes,
                dailyGoalXp: dailyGoalXp,
                preferredFocus: preferredFocus
            ),
            bearerToken: token
        )
    }

    func foundation() async throws -> IOSFoundationResponse {
        let token = try await authSession.bearerToken()
        return try await client.get(
            "/api/v3/ios/course/foundation",
            bearerToken: token
        )
    }

    func completeFoundation(
        speakingBonus: Bool,
        eventId: String
    ) async throws -> IOSFoundationCompleteResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/course/foundation/complete",
            body: IOSFoundationCompleteRequest(
                foundationId: "starter0_hsk1",
                foundationVersion: 1,
                speakingBonus: speakingBonus,
                eventId: eventId
            ),
            bearerToken: token
        )
    }

    func dictionary() async throws -> IOSDictionaryResponse {
        let token = try await authSession.bearerToken()
        return try await client.get(
            "/api/v3/ios/dictionary",
            bearerToken: token
        )
    }

    func lesson(
        order: Int,
        accessRef: String = ""
    ) async throws -> IOSLessonResponse {
        let token = try await authSession.bearerToken()
        var query: [URLQueryItem] = []
        if !accessRef.isEmpty {
            query.append(URLQueryItem(name: "access_ref", value: accessRef))
        }
        return try await client.get(
            "/api/v3/ios/course/lesson/\(order)",
            bearerToken: token,
            queryItems: query
        )
    }

    func completeLesson(
        order: Int,
        eventId: String,
        mistakes: [IOSCourseMistake],
        accessRef: String = ""
    ) async throws -> IOSCourseCompleteResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/course/complete",
            body: IOSCourseCompleteRequest(
                lessonOrder: order,
                eventId: eventId,
                mistakes: mistakes,
                accessRef: accessRef
            ),
            bearerToken: token
        )
    }
}
