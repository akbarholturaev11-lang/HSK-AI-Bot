import Foundation

@MainActor
final class DictionaryViewModel: ObservableObject {
    @Published private(set) var response: IOSDictionaryResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var errorKey: String?
    @Published var query = ""
    @Published var levelFilter = "all"

    private let api: IOSCourseAPI

    init(api: IOSCourseAPI) {
        self.api = api
    }

    var filteredWords: [IOSDictionaryWord] {
        guard let words = response?.words else { return [] }
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return words.filter { word in
            let levelOK = levelFilter == "all" || normalizedLevel(word.level) == levelFilter
            guard levelOK else { return false }
            guard !needle.isEmpty else { return true }
            return word.hanzi.lowercased().contains(needle)
                || word.pinyin.lowercased().contains(needle)
                || word.meaning.lowercased().contains(needle)
        }
    }

    func load(force: Bool = false) async {
        guard !isLoading else { return }
        if !force, response != nil { return }
        isLoading = true
        errorKey = nil
        do {
            let payload = try await api.dictionary()
            guard payload.ok else { throw DictionaryViewModelError.invalidPayload }
            response = payload
            isLoading = false
        } catch let error as APIError where error.isSessionExpired {
            isLoading = false
            errorKey = "error_session_expired"
        } catch {
            isLoading = false
            errorKey = "dictionary_load_error"
        }
    }

    func reset() {
        response = nil
        isLoading = false
        errorKey = nil
        query = ""
        levelFilter = "all"
    }

    private func normalizedLevel(_ value: String) -> String {
        let digits = value.filter(\.isNumber)
        if let first = digits.first { return "hsk\(first)" }
        let clean = value.lowercased().replacingOccurrences(of: " ", with: "")
        return clean.hasPrefix("hsk") ? clean : "hsk\(clean)"
    }
}

enum DictionaryViewModelError: Error {
    case invalidPayload
}
