import Foundation

actor AuthSession {
    private let api: IOSAuthAPI
    private let credentials: any CredentialStore
    private let appVersion: String
    private let now: @Sendable () -> Date

    /// Short-lived access token: memory only.
    private var accessToken: AccessToken?
    private var refreshTask: Task<AccessToken, Error>?

    init(
        api: IOSAuthAPI,
        credentials: any CredentialStore = KeychainCredentialStore(),
        appVersion: String = AppVersion.current,
        now: @escaping @Sendable () -> Date = Date.init
    ) {
        self.api = api
        self.credentials = credentials
        self.appVersion = appVersion
        self.now = now
    }

    func startLink() async throws -> PendingLink {
        let installationKey = try credentials.installationKey()
        let response = try await api.startLink(
            IOSLinkStartRequest(
                appVersion: appVersion,
                installationKey: installationKey
            )
        )

        guard
            response.ok,
            !response.linkRequestId.isEmpty,
            !response.displayCode.isEmpty,
            !response.pollingSecret.isEmpty,
            let botDeepLink = URL(string: response.botDeepLink)
        else {
            throw AuthSessionError.invalidResponse
        }

        return PendingLink(
            linkRequestId: response.linkRequestId,
            displayCode: response.displayCode,
            pollingSecret: response.pollingSecret,
            botDeepLink: botDeepLink,
            expiresAt: now().addingTimeInterval(TimeInterval(response.expiresIn))
        )
    }

    /// Returns false while Telegram approval is still pending.
    func pollLink(_ pending: PendingLink) async throws -> Bool {
        let response = try await api.linkStatus(
            IOSLinkStatusRequest(
                linkRequestId: pending.linkRequestId,
                pollingSecret: pending.pollingSecret
            )
        )

        guard response.status == "linked" else {
            return false
        }
        guard
            let refresh = response.refreshToken,
            !refresh.isEmpty,
            let access = response.accessToken,
            !access.isEmpty
        else {
            throw AuthSessionError.invalidResponse
        }

        // Persist the one-time returned refresh token before exposing success.
        try credentials.saveRefreshToken(refresh)
        accessToken = AccessToken(
            value: access,
            expiresAt: now().addingTimeInterval(
                TimeInterval(response.accessExpiresIn ?? 0)
            )
        )
        return true
    }

    func bootstrap() async throws -> LinkedAccount {
        guard try credentials.refreshToken() != nil else {
            throw AuthSessionError.sessionExpired
        }

        let token = try await validAccessToken()
        let response: IOSBootstrapResponse
        do {
            response = try await api.bootstrap(
                bearerToken: token,
                appVersion: appVersion
            )
        } catch let error as APIError where error.isSessionExpired {
            try clearLocalSession(unlinkDevice: false)
            throw AuthSessionError.sessionExpired
        }

        guard response.ok, response.authenticated else {
            try clearLocalSession(unlinkDevice: false)
            throw AuthSessionError.sessionExpired
        }

        return LinkedAccount(
            deviceId: response.device.id,
            displayName: response.user.name,
            language: response.user.language,
            level: response.user.level,
            accessState: response.user.accessState,
            isPaid: response.user.isPaid
        )
    }

    func bearerToken() async throws -> String {
        try await validAccessToken()
    }

    func logout(unlinkDevice: Bool = false) async {
        if let token = try? await validAccessToken() {
            _ = try? await api.revoke(
                bearerToken: token,
                unlinkDevice: unlinkDevice
            )
        }
        try? clearLocalSession(unlinkDevice: unlinkDevice)
    }

    func invalidateSession() {
        try? clearLocalSession(unlinkDevice: false)
    }

    private func validAccessToken() async throws -> String {
        let currentDate = now()
        if let accessToken, accessToken.isUsable(at: currentDate) {
            return accessToken.value
        }

        if let refreshTask {
            return try await refreshTask.value.value
        }

        guard let storedRefresh = try credentials.refreshToken() else {
            throw AuthSessionError.sessionExpired
        }

        let api = self.api
        let credentials = self.credentials
        let now = self.now
        let task = Task<AccessToken, Error> {
            let response = try await api.refresh(
                IOSRefreshRequest(refreshToken: storedRefresh)
            )
            guard
                response.ok,
                !response.accessToken.isEmpty,
                !response.refreshToken.isEmpty
            else {
                throw AuthSessionError.sessionExpired
            }

            // Refresh tokens rotate. Durable replace happens before the old
            // in-memory access token is considered refreshed.
            try credentials.saveRefreshToken(response.refreshToken)
            return AccessToken(
                value: response.accessToken,
                expiresAt: now().addingTimeInterval(
                    TimeInterval(response.accessExpiresIn)
                )
            )
        }
        refreshTask = task

        do {
            let token = try await task.value
            refreshTask = nil
            accessToken = token
            return token.value
        } catch {
            refreshTask = nil
            if
                (error as? AuthSessionError) == .sessionExpired
                || (error as? APIError)?.isSessionExpired == true
            {
                try? clearLocalSession(unlinkDevice: false)
                throw AuthSessionError.sessionExpired
            }
            throw error
        }
    }

    private func clearLocalSession(unlinkDevice: Bool) throws {
        accessToken = nil
        refreshTask?.cancel()
        refreshTask = nil
        if unlinkDevice {
            try credentials.clearEverything()
        } else {
            try credentials.clearSession()
        }
    }
}
