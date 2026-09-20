import Foundation

struct IOSLinkStartRequest: Encodable, Sendable {
    let platform = "ios"
    let appVersion: String
    let installationKey: String
}

struct IOSLinkStartResponse: Decodable, Sendable {
    let ok: Bool
    let status: String
    let linkRequestId: String
    let displayCode: String
    let pollingSecret: String
    let botDeepLink: String
    let expiresIn: Int
}

struct IOSLinkStatusRequest: Encodable, Sendable {
    let linkRequestId: String
    let pollingSecret: String
}

struct IOSLinkStatusResponse: Decodable, Sendable {
    let ok: Bool
    let status: String
    let expiresIn: Int
    let accessToken: String?
    let accessExpiresIn: Int?
    let refreshToken: String?
    let refreshExpiresIn: Int?
}

struct IOSRefreshRequest: Encodable, Sendable {
    let refreshToken: String
}

struct IOSRefreshResponse: Decodable, Sendable {
    let ok: Bool
    let accessToken: String
    let accessExpiresIn: Int
    let refreshToken: String
    let refreshExpiresIn: Int
}

struct IOSRevokeRequest: Encodable, Sendable {
    let revokeDevice: Bool
}

struct IOSRevokeResponse: Decodable, Sendable {
    let ok: Bool
    let deviceRevoked: Bool
}

struct IOSBootstrapResponse: Decodable, Sendable {
    let ok: Bool
    let authenticated: Bool
    let firstOpen: Bool
    let versionUpgraded: Bool
    let device: IOSBootstrapDevice
    let user: IOSBootstrapUser
}

struct IOSBootstrapDevice: Decodable, Sendable {
    let id: String
    let platform: String
    let appVersion: String
}

struct IOSBootstrapUser: Decodable, Sendable {
    let name: String
    let language: String
    let level: String
    let accessState: String
    let isPaid: Bool
}

struct PendingLink: Sendable, Equatable {
    let linkRequestId: String
    let displayCode: String
    let pollingSecret: String
    let botDeepLink: URL
    let expiresAt: Date
}

struct LinkedAccount: Sendable, Equatable {
    let displayName: String
    let language: String
    let level: String
    let accessState: String
    let isPaid: Bool
}

struct AccessToken: Sendable, Equatable {
    let value: String
    let expiresAt: Date

    func isUsable(at date: Date, skew: TimeInterval = 30) -> Bool {
        !value.isEmpty && date < expiresAt.addingTimeInterval(-skew)
    }
}

enum AuthSessionError: Error, Equatable {
    case invalidResponse
    case sessionExpired
}
