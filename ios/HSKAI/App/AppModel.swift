import Foundation

@MainActor
final class AppModel: ObservableObject {
    enum Phase {
        case launching
        case signedOut
        case onboarding(LinkedAccount)
        case main(LinkedAccount)
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

    struct OnboardingPresentation: Equatable {
        var step = 0
        var selectedLevel = "beginner"
        var selectedGoal = "hsk_exam"
        var isSubmitting = false
        var errorKey: String?
    }

    @Published private(set) var phase: Phase = .launching
    @Published private(set) var link = LinkPresentation()
    @Published private(set) var onboarding = OnboardingPresentation()

    private let authSession: AuthSession
    private let courseAPI: IOSCourseAPI
    let courseViewModel: CourseViewModel
    let dictionaryViewModel: DictionaryViewModel
    let practiceViewModel: PracticeViewModel
    let mistakesViewModel: MistakesViewModel
    let examViewModel: ExamViewModel
    let wordDrillViewModel: WordDrillViewModel
    let pronunciationDrillViewModel: PronunciationDrillViewModel
    let ratingViewModel: RatingViewModel
    let subscriptionViewModel: SubscriptionViewModel
    let challengeViewModel: ChallengeViewModel
    let voiceViewModel: VoiceViewModel
    let assistantViewModel: AssistantViewModel
    let adViewModel: AdViewModel
    let reminderManager = StudyReminderManager()
    private var pendingLink: PendingLink?
    private var pollingTask: Task<Void, Never>?
    private var didRestore = false

    init(environment: AppEnvironment) {
        let client = APIClient(environment: environment)
        let authSession = AuthSession(api: IOSAuthAPI(client: client))
        let courseAPI = IOSCourseAPI(client: client, authSession: authSession)
        self.authSession = authSession
        self.courseAPI = courseAPI
        self.courseViewModel = CourseViewModel(api: courseAPI)
        self.dictionaryViewModel = DictionaryViewModel(api: courseAPI)
        let practiceAPI = IOSPracticeAPI(client: client, authSession: authSession)
        self.practiceViewModel = PracticeViewModel(api: practiceAPI)
        self.mistakesViewModel = MistakesViewModel(api: practiceAPI)
        self.examViewModel = ExamViewModel(api: practiceAPI)
        self.wordDrillViewModel = WordDrillViewModel(
            practiceAPI: practiceAPI,
            courseAPI: courseAPI
        )
        self.pronunciationDrillViewModel = PronunciationDrillViewModel(
            practiceAPI: practiceAPI,
            courseAPI: courseAPI
        )
        self.ratingViewModel = RatingViewModel(
            api: IOSSocialAPI(client: client, authSession: authSession)
        )
        self.challengeViewModel = ChallengeViewModel(api: IOSChallengeAPI(client: client, authSession: authSession))
        self.voiceViewModel = VoiceViewModel(api: IOSVoiceAPI(client: client, authSession: authSession))
        self.assistantViewModel = AssistantViewModel(api: IOSAssistantAPI(client: client, authSession: authSession))
        self.adViewModel = AdViewModel(api: IOSAdAPI(client: client, authSession: authSession))
        self.subscriptionViewModel = SubscriptionViewModel(
            api: IOSSubscriptionAPI(client: client, authSession: authSession)
        )
    }

    func restoreSession() async {
        guard !didRestore else { return }
        didRestore = true

        do {
            let account = try await authSession.bootstrap()
            await routeAfterAuthentication(account)
        } catch AuthSessionError.sessionExpired {
            phase = .signedOut
        } catch {
            phase = .bootstrapFailed
        }
    }

    func retryBootstrap() async {
        phase = .launching
        do {
            let account = try await authSession.bootstrap()
            await routeAfterAuthentication(account)
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

    func selectOnboardingLevel(_ level: String) {
        guard Self.levels.contains(level), !onboarding.isSubmitting else { return }
        onboarding.selectedLevel = level
        onboarding.errorKey = nil
    }

    func selectOnboardingGoal(_ goal: String) {
        guard Self.goals.contains(goal), !onboarding.isSubmitting else { return }
        onboarding.selectedGoal = goal
        onboarding.errorKey = nil
    }

    func onboardingBack() {
        guard !onboarding.isSubmitting else { return }
        onboarding.step = max(0, onboarding.step - 1)
        onboarding.errorKey = nil
    }

    func onboardingNext(account: LinkedAccount) async {
        guard !onboarding.isSubmitting else { return }
        if onboarding.step < 2 {
            onboarding.step += 1
            onboarding.errorKey = nil
            return
        }

        onboarding.isSubmitting = true
        onboarding.errorKey = nil
        do {
            let result = try await courseAPI.completeOnboarding(
                level: onboarding.selectedLevel,
                goal: onboarding.selectedGoal,
                language: Self.backendLanguage(account.language),
                timezoneOffsetMinutes: Self.timezoneOffsetMinutes()
            )
            guard result.ok else {
                onboarding.isSubmitting = false
                onboarding.errorKey = "onboarding_save_error"
                return
            }

            let updatedAccount = LinkedAccount(
                deviceId: account.deviceId,
                displayName: account.displayName,
                language: account.language,
                level: result.level.isEmpty ? onboarding.selectedLevel : result.level,
                accessState: account.accessState,
                isPaid: account.isPaid
            )
            onboarding.isSubmitting = false
            phase = .main(updatedAccount)
        } catch let error as APIError where error.isSessionExpired {
            onboarding.isSubmitting = false
            await authSession.invalidateSession()
            phase = .signedOut
        } catch {
            onboarding.isSubmitting = false
            onboarding.errorKey = "onboarding_save_error"
        }
    }

    func logout() async {
        pollingTask?.cancel()
        await authSession.logout()
        link = LinkPresentation()
        onboarding = OnboardingPresentation()
        courseViewModel.reset()
        dictionaryViewModel.reset()
        practiceViewModel.reset()
        mistakesViewModel.reset()
        examViewModel.resetToCenter()
        wordDrillViewModel.reset()
        pronunciationDrillViewModel.reset()
        ratingViewModel.reset()
        subscriptionViewModel.reset()
        challengeViewModel.reset()
        voiceViewModel.reset()
        assistantViewModel.reset()
        adViewModel.reset()
        phase = .signedOut
    }

    private func routeAfterAuthentication(_ account: LinkedAccount) async {
        do {
            let status = try await courseAPI.onboardingStatus()
            guard status.ok else {
                phase = .bootstrapFailed
                return
            }
            if status.completed {
                phase = .main(account)
            } else {
                onboarding = OnboardingPresentation(
                    step: 0,
                    selectedLevel: Self.normalizedLevel(status.level),
                    selectedGoal: Self.normalizedGoal(status.profile.goal),
                    isSubmitting: false,
                    errorKey: nil
                )
                phase = .onboarding(account)
            }
        } catch let error as APIError where error.isSessionExpired {
            await authSession.invalidateSession()
            phase = .signedOut
        } catch {
            phase = .bootstrapFailed
        }
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
                            let account = try await self.authSession.bootstrap()
                            await self.routeAfterAuthentication(account)
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

    private static func normalizedLevel(_ level: String) -> String {
        let value = level.lowercased()
        return levels.contains(value) ? value : "beginner"
    }

    private static func normalizedGoal(_ goal: String) -> String {
        goals.contains(goal) ? goal : "hsk_exam"
    }

    private static func backendLanguage(_ language: String) -> String {
        switch language.lowercased() {
        case "uz": return "uz"
        case "tg", "tj": return "tj"
        default: return "ru"
        }
    }

    private static func timezoneOffsetMinutes() -> Int {
        let raw = TimeZone.current.secondsFromGMT() / 60
        return min(840, max(-720, raw))
    }

    private static let levels = Set(["beginner", "hsk1", "hsk2", "hsk3", "hsk4"])
    private static let goals = Set([
        "hsk_exam",
        "study_china",
        "work_china",
        "daily_communication",
        "travel",
    ])

    deinit {
        pollingTask?.cancel()
    }
}
