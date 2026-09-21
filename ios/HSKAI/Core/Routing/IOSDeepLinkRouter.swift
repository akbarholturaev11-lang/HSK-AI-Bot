import Foundation

enum IOSDeepLinkDestination: Equatable, Sendable {
    case course
    case practice
    case dictionary
    case rating
    case profile
}

enum IOSDeepLinkRouter {
    static func destination(for url: URL) -> IOSDeepLinkDestination? {
        guard url.scheme?.lowercased() == "pomp-hsk-ai" else { return nil }
        let raw = [url.host, url.pathComponents.dropFirst().first]
            .compactMap { $0 }
            .first { !$0.isEmpty }?
            .lowercased()
        switch raw {
        case "course": return .course
        case "practice": return .practice
        case "dictionary": return .dictionary
        case "rating": return .rating
        case "profile": return .profile
        default: return nil
        }
    }
}
