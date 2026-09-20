import Foundation

enum APIError: Error, Equatable {
    case invalidPath
    case originViolation
    case invalidResponse
    case httpStatus(Int)
    case server(code: String, status: Int)
    case emptyResponse
    case transport
    case decoding
    case encoding

    var isSessionExpired: Bool {
        switch self {
        case .server(_, let status), .httpStatus(let status):
            return status == 401
        default:
            return false
        }
    }
}

struct APIErrorEnvelope: Decodable, Sendable {
    let ok: Bool?
    let error: String?
}
