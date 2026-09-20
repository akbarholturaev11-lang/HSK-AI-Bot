import Foundation

@MainActor
final class CourseViewModel: ObservableObject {
    @Published private(set) var map: IOSCourseMap?
    @Published private(set) var isLoading = false
    @Published private(set) var isRefreshing = false
    @Published private(set) var isStale = false
    @Published private(set) var errorKey: String?

    let api: IOSCourseAPI
    private let cache: CourseMapCache
    private var loadedScope: String?

    init(api: IOSCourseAPI, cache: CourseMapCache = CourseMapCache()) {
        self.api = api
        self.cache = cache
    }

    func load(scope: String, force: Bool = false) async {
        guard !isRefreshing else { return }
        if !force, loadedScope == scope, map != nil { return }

        isLoading = map == nil
        isRefreshing = true
        errorKey = nil

        if map == nil, let cached = await cache.load(scope: scope) {
            map = cached
            isLoading = false
            isStale = false
        }

        do {
            let fresh = try await api.courseMap()
            guard fresh.ok else { throw CourseViewModelError.invalidPayload }
            map = fresh
            loadedScope = scope
            isLoading = false
            isRefreshing = false
            isStale = false
            await cache.save(fresh, scope: scope)
        } catch let error as APIError where error.isSessionExpired {
            isLoading = false
            isRefreshing = false
            errorKey = "error_session_expired"
        } catch {
            isLoading = false
            isRefreshing = false
            if map != nil { isStale = true }
            else { errorKey = "error_network" }
        }
    }

    func reset() {
        map = nil
        loadedScope = nil
        isLoading = false
        isRefreshing = false
        isStale = false
        errorKey = nil
    }
}

enum CourseViewModelError: Error {
    case invalidPayload
}
