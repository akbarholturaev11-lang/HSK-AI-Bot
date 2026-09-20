import Foundation

enum APIError: Error, Equatable {
    case invalidPath
    case originViolation
    case invalidResponse
    case httpStatus(Int)
    case emptyResponse
    case transport
    case decoding
    case encoding
}
