import Foundation

struct APIClient: Sendable {
    let environment: AppEnvironment
    let session: URLSession

    init(
        environment: AppEnvironment,
        session: URLSession = .shared
    ) {
        self.environment = environment
        self.session = session
    }

    func get<Response: Decodable & Sendable>(
        _ path: String,
        bearerToken: String? = nil,
        queryItems: [URLQueryItem] = [],
        as type: Response.Type = Response.self
    ) async throws -> Response {
        var request = try makeRequest(
            path: path,
            method: "GET",
            bearerToken: bearerToken,
            queryItems: queryItems
        )
        request.httpBody = nil
        return try await send(request, as: type)
    }

    func post<Body: Encodable, Response: Decodable & Sendable>(
        _ path: String,
        body: Body,
        bearerToken: String? = nil,
        as type: Response.Type = Response.self
    ) async throws -> Response {
        var request = try makeRequest(
            path: path,
            method: "POST",
            bearerToken: bearerToken
        )
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            request.httpBody = try encoder.encode(body)
        } catch {
            throw APIError.encoding
        }
        return try await send(request, as: type)
    }

    func makeRequest(
        path: String,
        method: String,
        bearerToken: String? = nil,
        queryItems: [URLQueryItem] = []
    ) throws -> URLRequest {
        guard path.hasPrefix("/"), !path.hasPrefix("//") else {
            throw APIError.invalidPath
        }

        guard var components = URLComponents(
            url: environment.apiBaseURL.appending(path: String(path.dropFirst())),
            resolvingAgainstBaseURL: false
        ) else {
            throw APIError.invalidPath
        }
        components.queryItems = queryItems.isEmpty ? nil : queryItems

        guard let url = components.url else {
            throw APIError.invalidPath
        }
        guard
            url.scheme == environment.apiBaseURL.scheme,
            url.host == environment.apiBaseURL.host,
            url.port == environment.apiBaseURL.port
        else {
            throw APIError.originViolation
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 20
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let bearerToken, !bearerToken.isEmpty {
            request.setValue("Bearer \(bearerToken)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func send<Response: Decodable & Sendable>(
        _ request: URLRequest,
        as type: Response.Type
    ) async throws -> Response {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            if
                let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data),
                let code = envelope.error,
                !code.isEmpty
            {
                throw APIError.server(code: code, status: http.statusCode)
            }
            throw APIError.httpStatus(http.statusCode)
        }
        guard !data.isEmpty else {
            throw APIError.emptyResponse
        }

        do {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(type, from: data)
        } catch {
            throw APIError.decoding
        }
    }
}
