import Foundation

struct IOSAuthAPI: Sendable {
    let client: APIClient

    func startLink(_ body: IOSLinkStartRequest) async throws -> IOSLinkStartResponse {
        try await client.post(
            "/api/v3/ios-auth/link/start",
            body: body
        )
    }

    func linkStatus(_ body: IOSLinkStatusRequest) async throws -> IOSLinkStatusResponse {
        try await client.post(
            "/api/v3/ios-auth/link/status",
            body: body
        )
    }

    func refresh(_ body: IOSRefreshRequest) async throws -> IOSRefreshResponse {
        try await client.post(
            "/api/v3/ios-auth/refresh",
            body: body
        )
    }

    func revoke(
        bearerToken: String,
        unlinkDevice: Bool
    ) async throws -> IOSRevokeResponse {
        try await client.post(
            "/api/v3/ios-auth/revoke",
            body: IOSRevokeRequest(revokeDevice: unlinkDevice),
            bearerToken: bearerToken
        )
    }

    func bootstrap(
        bearerToken: String,
        appVersion: String
    ) async throws -> IOSBootstrapResponse {
        try await client.get(
            "/api/v3/ios/bootstrap",
            bearerToken: bearerToken,
            queryItems: [URLQueryItem(name: "app_version", value: appVersion)]
        )
    }
}
