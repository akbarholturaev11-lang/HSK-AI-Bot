import Foundation

struct IOSPracticeAPI: Sendable {
    let client: APIClient
    let authSession: AuthSession

    func start(
        mode: String,
        level: String,
        language: String,
        skill: String = "",
        accessRef: String = "",
        adSupported: Bool = false
    ) async throws -> IOSPracticeStartResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/practice/start",
            body: IOSPracticeStartRequest(
                mode: mode,
                level: level,
                language: language,
                skill: skill,
                accessRef: accessRef,
                adSupported: adSupported
            ),
            bearerToken: token
        )
    }

    func complete(
        session: IOSPracticeSession,
        language: String,
        answers: [String: Int],
        accessRef: String = "",
        adSupported: Bool = false
    ) async throws -> IOSPracticeCompleteResponse {
        let token = try await authSession.bearerToken()
        let ordered = session.questions.compactMap { question -> IOSPracticeAnswer? in
            guard let selected = answers[question.id] else { return nil }
            return IOSPracticeAnswer(questionId: question.id, selected: selected)
        }

        return try await client.post(
            "/api/v3/ios/practice/complete",
            body: IOSPracticeCompleteRequest(
                mode: session.mode,
                level: session.level,
                language: language,
                skill: session.skill,
                sessionId: session.id,
                answers: ordered,
                accessRef: accessRef,
                adSupported: adSupported
            ),
            bearerToken: token
        )
    }
}
