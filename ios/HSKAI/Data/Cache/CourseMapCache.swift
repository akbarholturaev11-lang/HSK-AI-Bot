import Foundation

actor CourseMapCache {
    private let directory: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(fileManager: FileManager = .default) {
        self.directory = fileManager.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? fileManager.temporaryDirectory

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        self.encoder = encoder
    }

    func load(scope: String) -> IOSCourseMap? {
        guard let url = cacheURL(scope: scope),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(IOSCourseMap.self, from: data)
    }

    func save(_ map: IOSCourseMap, scope: String) {
        guard let url = cacheURL(scope: scope),
              let data = try? encoder.encode(map) else { return }
        try? data.write(to: url, options: [.atomic])
    }

    private func cacheURL(scope: String) -> URL? {
        let safe = String(scope.filter {
            $0.isLetter || $0.isNumber || $0 == "-"
        }.prefix(80))
        guard !safe.isEmpty else { return nil }
        return directory.appendingPathComponent("hskai-course-\(safe).json")
    }
}
