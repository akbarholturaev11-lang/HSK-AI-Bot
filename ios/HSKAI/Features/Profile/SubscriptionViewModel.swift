import Foundation

@MainActor
final class SubscriptionViewModel: ObservableObject {
    @Published private(set) var overview: IOSSubscriptionOverview?
    @Published private(set) var trial: IOSTrialStatus?
    @Published private(set) var isLoading = false
    @Published private(set) var errorKey: String?

    private let api: IOSSubscriptionAPI

    init(api: IOSSubscriptionAPI) { self.api = api }

    func load() async {
        guard !isLoading else { return }
        isLoading = true
        errorKey = nil
        do {
            async let overview = api.overview()
            async let trial = api.trialStatus()
            self.overview = try await overview
            self.trial = try await trial
        } catch {
            errorKey = "subscription_load_error"
        }
        isLoading = false
    }

    func startTrial() async {
        guard !isLoading else { return }
        isLoading = true
        errorKey = nil
        do {
            trial = try await api.startTrial()
            overview = try? await api.overview()
        } catch {
            errorKey = "subscription_trial_error"
        }
        isLoading = false
    }

    func reset() {
        overview = nil
        trial = nil
        isLoading = false
        errorKey = nil
    }
}
