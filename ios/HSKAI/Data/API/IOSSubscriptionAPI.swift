import Foundation

struct IOSSubscriptionAPI: Sendable {
    let client: APIClient
    let authSession: AuthSession

    func overview() async throws -> IOSSubscriptionOverview {
        let token = try await authSession.bearerToken()
        return try await client.get("/api/v3/ios/subscription/overview", bearerToken: token)
    }

    func trialStatus() async throws -> IOSTrialStatus {
        let token = try await authSession.bearerToken()
        return try await client.get("/api/v3/ios/subscription/trial", bearerToken: token)
    }

    func startTrial() async throws -> IOSTrialStatus {
        let token = try await authSession.bearerToken()
        return try await client.post(
            "/api/v3/ios/subscription/trial/start",
            body: EmptyBody(),
            bearerToken: token
        )
    }
}

private struct EmptyBody: Encodable {}
