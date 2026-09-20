import Foundation

struct AppEnvironment: Sendable {
    let apiBaseURL: URL

    static let production = AppEnvironment(
        apiBaseURL: URL(string: "https://telegram-chinese-bot-production.up.railway.app")!
    )

    init(apiBaseURL: URL) {
        precondition(apiBaseURL.scheme == "https", "HSK AI API origin must use HTTPS")
        precondition(apiBaseURL.host != nil, "HSK AI API origin must include a host")
        self.apiBaseURL = apiBaseURL
    }
}
