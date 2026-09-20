import Foundation

@MainActor
final class AppModel: ObservableObject {
    enum Phase {
        case launching
        case signedOut
        case authenticated(LinkedAccount)
        case bootstrapFailed
    }

    struct LinkPresentation: Equatable {
        var isRequesting = false
        var displayCode = ""
        var botDeepLink: URL?
        var secondsRemaining = 0
        var isWaitingForApproval = false
        var isExpired = false
        var errorKey: String?
    }

    @Published private(set) var phase: Phase = .launching
    @Published private(set) var link = LinkPresentation()

    private let authSession: AuthSession
    private var pendingLink: PendingLink?
    private var pollingTask: Task<Void, Never>?
    private var didRestore = false

    init(environment: AppEnvironment) {
        let client = APIClient(environment: environment)
        self.authSession = AuthSession(api: IOSAuthAPI(client: client))
    }

    func restoreSession() async {
        guard !didRestore else { return }
        didRestore = true

        do {
            phase = .authenticated(try await authSession.bootstrap())
        } catch AuthSessionError.sessionExpired {
            phase = .signedOut
        } catch {
            phase = .bootstrapFailed
        }
    }

    func retryBootstrap() async {
        phase = .launching
        do {
            phase = .authenticated(try await authSession.bootstrap())
        } catch AuthSessionError.sessionExpired {
            phase = .signedOut
        } catch {
            phase = .bootstrapFailed
        }
    }

    func requestLink() async {
        pollingTask?.cancel()
        pendingLink = nil
        link = LinkPresentation(isRequesting: true)

        do {
            let pending = try await authSession.startLink()
            pendingLink = pending
            link = LinkPresentation(
                isRequesting: false,
                displayCode: pending.displayCode,
                botDeepLink: pending.botDeepLink,
                secondsRemaining: remainingSeconds(for: pending),
                isWaitingForApproval: true,
                isExpired: false,
                errorKey: nil
            )
            startPolling(pending)
        } catch {
            link = LinkPresentation(errorKey: authErrorKey(error))
        }
    }

    func clearLinkError() {
        link.errorKey = nil
    }

    private func startPolling(_ pending: PendingLink) {
        pollingTask?.cancel()
        pollingTask = Task { [weak self] in
            guard let self else { return }

            while !Task.isCancelled {
                let remaining = self.remainingSeconds(for: pending)
                self.link.secondsRemaining = remaining

                if remaining <= 0 {
                    self.link.isWaitingForApproval = false
                    self.link.isExpired = true
                    return
                }

                do {
                    if try await self.authSession.pollLink(pending) {
                        self.link.isWaitingForApproval = false
                        self.phase = .launching
                        do {
                            self.phase = .authenticated(
                                try await self.authSession.bootstrap()
                            )
                        } catch {
                            self.phase = .bootstrapFailed
                        }
                        return
                    }
                } catch {
                    if self.isTransient(error) {
                        // Keep the pending link alive while the device is briefly offline.
                    } else {
                        self.link.isWaitingForApproval = false
                        self.link.isExpired = true
                        self.link.errorKey = self.authErrorKey(error)
                        return
                    }
                }

                do {
                    try await Task.sleep(nanoseconds: 2_000_000_000)
                } catch {
                    return
                }
            }
        }
    }

    private func remainingSeconds(for pending: PendingLink) -> Int {
        max(0, Int(pending.expiresAt.timeIntervalSinceNow.rounded(.down)))
    }

    private func isTransient(_ error: Error) -> Bool {
        guard let apiError = error as? APIError else { return false }
        switch apiError {
        case .transport:
            return true
        default:
            return false
        }
    }

    private func authErrorKey(_ error: Error) -> String {
        if let apiError = error as? APIError {
            switch apiError {
            case .server(let code, _):
                switch code {
                case "desktop_link_rate_limited":
                    return "error_link_rate_limited"
                case "desktop_device_bound_to_other_user":
                    return "error_device_bound"
                case "desktop_link_invalid",
                     "desktop_link_expired",
                     "desktop_link_consumed",
                     "desktop_link_already_approved":
                    return "error_link_invalid"
                case "ios_auth_unavailable":
                    return "error_auth_unavailable"
                default:
                    return "error_network"
                }
            case .transport:
                return "error_network"
            default:
                return "error_auth_unavailable"
            }
        }

        if let sessionError = error as? AuthSessionError,
           sessionError == .sessionExpired {
            return "error_session_expired"
        }
        return "error_auth_unavailable"
    }

    deinit {
        pollingTask?.cancel()
    }
}
