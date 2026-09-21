import Foundation

@MainActor
final class PracticeViewModel: ObservableObject {
    enum Phase: Equatable {
        case home
        case loading
        case session
        case completing
        case result
    }

    @Published private(set) var phase: Phase = .home
    @Published private(set) var session: IOSPracticeSession?
    @Published private(set) var questionIndex = 0
    @Published private(set) var selectedIndex: Int?
    @Published private(set) var answers: [String: Int] = [:]
    @Published private(set) var result: IOSPracticeCompleteResponse?
    @Published private(set) var errorKey: String?

    private let api: IOSPracticeAPI
    private let speech = MandarinSpeechPlayer()
    private var language = "ru"
    private var accessRef = ""
    private var adSupported = false

    init(api: IOSPracticeAPI) {
        self.api = api
    }

    var currentQuestion: IOSPracticeQuestion? {
        guard let session, session.questions.indices.contains(questionIndex) else {
            return nil
        }
        return session.questions[questionIndex]
    }

    var progress: Double {
        guard let session, !session.questions.isEmpty else { return 0 }
        return Double(questionIndex + 1) / Double(session.questions.count)
    }

    func startPlacement(level: String, language: String) async {
        guard phase != .loading && phase != .completing else { return }
        phase = .loading
        errorKey = nil
        self.language = Self.backendLanguage(language)
        accessRef = ""
        adSupported = false

        do {
            let response = try await api.start(
                mode: "placement",
                level: Self.normalizedLevel(level),
                language: self.language
            )
            guard let session = response.session,
                  response.ok,
                  !session.id.isEmpty,
                  !session.questions.isEmpty
            else {
                throw PracticeViewModelError.invalidPayload
            }

            self.session = session
            questionIndex = 0
            selectedIndex = nil
            answers = [:]
            result = nil
            phase = .session
        } catch let error as APIError {
            phase = .home
            errorKey = Self.errorKey(error)
        } catch {
            phase = .home
            errorKey = "practice_start_error"
        }
    }

    func select(_ index: Int) {
        guard phase == .session,
              selectedIndex == nil,
              let question = currentQuestion,
              question.options.indices.contains(index)
        else { return }
        selectedIndex = index
    }

    func playCurrentAudio() {
        guard let question = currentQuestion else { return }
        let text = question.audioText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty {
            speech.play(text)
        }
    }

    func advance() async {
        guard phase == .session,
              let session,
              let question = currentQuestion,
              let selectedIndex
        else { return }

        answers[question.id] = selectedIndex

        if questionIndex < session.questions.count - 1 {
            questionIndex += 1
            self.selectedIndex = nil
            return
        }

        phase = .completing
        errorKey = nil
        do {
            let completed = try await api.complete(
                session: session,
                language: language,
                answers: answers,
                accessRef: accessRef,
                adSupported: adSupported
            )
            guard completed.ok else {
                throw PracticeViewModelError.invalidPayload
            }
            result = completed
            phase = .result
        } catch let error as APIError {
            phase = .session
            errorKey = Self.errorKey(error)
        } catch {
            phase = .session
            errorKey = "practice_save_error"
        }
    }

    func reset() {
        speech.stop()
        phase = .home
        session = nil
        questionIndex = 0
        selectedIndex = nil
        answers = [:]
        result = nil
        errorKey = nil
        accessRef = ""
        adSupported = false
    }

    private static func normalizedLevel(_ level: String) -> String {
        let value = level.lowercased()
        if ["hsk1", "hsk2", "hsk3", "hsk4"].contains(value) {
            return value
        }
        return "hsk1"
    }

    private static func backendLanguage(_ language: String) -> String {
        switch language.lowercased() {
        case "uz": return "uz"
        case "tj", "tg": return "tj"
        default: return "ru"
        }
    }

    private static func errorKey(_ error: APIError) -> String {
        switch error {
        case .server(let code, _):
            switch code {
            case "free_feature_limit_reached", "access_start_first", "course_access_blocked":
                return "practice_limit_error"
            case "ad_authorization_required", "invalid_ad_authorization":
                return "practice_access_error"
            default:
                return "practice_start_error"
            }
        case .transport:
            return "error_network"
        default:
            return "practice_start_error"
        }
    }

    deinit {
        Task { @MainActor [speech] in
            speech.stop()
        }
    }
}

enum PracticeViewModelError: Error {
    case invalidPayload
}
