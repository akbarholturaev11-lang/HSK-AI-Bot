import Foundation

@MainActor
final class RatingViewModel: ObservableObject {
    @Published private(set) var rating: IOSRatingResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var referral: IOSReferralResponse?
    @Published private(set) var errorKey: String?

    private let api: IOSSocialAPI

    init(api: IOSSocialAPI) { self.api = api }

    func load() async {
        guard !isLoading else { return }
        isLoading = true
        errorKey = nil
        do {
            let response = try await api.rating()
            guard response.ok else { throw RatingViewModelError.invalidPayload }
            rating = response
            referral = try? await api.referral()
        } catch {
            errorKey = "rating_load_error"
        }
        isLoading = false
    }

    func reset() {
        rating = nil
        referral = nil
        isLoading = false
        errorKey = nil
    }
}

enum RatingViewModelError: Error { case invalidPayload }
