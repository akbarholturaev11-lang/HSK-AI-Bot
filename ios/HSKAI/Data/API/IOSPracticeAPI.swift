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

    func startExam(
        level: String,
        language: String,
        accessRef: String = "",
        adSupported: Bool = false
    ) async throws -> IOSExamStartResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/exams/start",
            body: IOSExamStartRequest(
                level: level,
                language: language,
                accessRef: accessRef,
                adSupported: adSupported
            ),
            bearerToken: token
        )
    }

    func completeExam(
        session: IOSExamSession,
        language: String,
        answers: [String: Int]
    ) async throws -> IOSExamCompleteResponse {
        let token = try await authSession.bearerToken()
        let ordered = session.questions.compactMap { question -> IOSExamAnswer? in
            guard let selected = answers[question.id] else { return nil }
            return IOSExamAnswer(
                questionId: question.id,
                selectedIndex: selected
            )
        }

        return try await client.post(
            "/api/v3/ios/exams/complete",
            body: IOSExamCompleteRequest(
                sessionId: session.id,
                level: session.level,
                language: language,
                answers: ordered
            ),
            bearerToken: token
        )
    }

    func mistakes(
        category: String? = nil,
        limit: Int = 100,
        offset: Int = 0
    ) async throws -> IOSMistakesOverviewResponse {
        let token = try await authSession.bearerToken()
        var query = [
            URLQueryItem(name: "limit", value: String(min(100, max(1, limit)))),
            URLQueryItem(name: "offset", value: String(max(0, offset))),
        ]
        if let category, !category.isEmpty, category != "all" {
            query.append(URLQueryItem(name: "category", value: category))
        }
        return try await client.get(
            "/api/v3/ios/mistakes",
            bearerToken: token,
            queryItems: query
        )
    }

    func startMistakeReview() async throws -> IOSMistakeReviewStartResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/mistakes/review/start",
            body: IOSMistakeReviewStartRequest(
                adSupported: false,
                accessRef: ""
            ),
            bearerToken: token
        )
    }

    func answerMistakeReview(
        sessionId: String,
        questionId: String,
        selectedIndex: Int
    ) async throws -> IOSMistakeReviewAnswerResponse {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/mistakes/review/answer",
            body: IOSMistakeReviewAnswerRequest(
                sessionId: sessionId,
                questionId: questionId,
                selectedIndex: selectedIndex
            ),
            bearerToken: token
        )
    }

    func completeMistakeReview(
        sessionId: String,
        answers: [String: Int],
        questions: [IOSMistakeReviewQuestion]
    ) async throws -> IOSMistakeReviewCompleteResponse {
        let token = try await authSession.bearerToken()
        let ordered = questions.compactMap { question -> IOSMistakeReviewCompleteAnswer? in
            guard let selected = answers[question.id] else { return nil }
            return IOSMistakeReviewCompleteAnswer(
                questionId: question.id,
                selectedIndex: selected
            )
        }
        return try await client.post(
            "/api/v3/ios/mistakes/review/complete",
            body: IOSMistakeReviewCompleteRequest(
                sessionId: sessionId,
                answers: ordered
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
