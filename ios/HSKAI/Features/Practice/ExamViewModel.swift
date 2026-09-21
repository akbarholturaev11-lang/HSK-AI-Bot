import Foundation

@MainActor
final class ExamViewModel: ObservableObject {
    enum Phase: Equatable {
        case center
        case loading
        case exam
        case completing
        case result
    }

    @Published private(set) var phase: Phase = .center
    @Published private(set) var session: IOSExamSession?
    @Published private(set) var questionIndex = 0
    @Published private(set) var selectedIndex: Int?
    @Published private(set) var answers: [String: Int] = [:]
    @Published private(set) var result: IOSExamCompleteResponse?
    @Published private(set) var errorKey: String?

    private let api: IOSPracticeAPI
    private let speech = MandarinSpeechPlayer()
    private var language = "ru"

    init(api: IOSPracticeAPI) {
        self.api = api
    }

    var currentQuestion: IOSExamQuestion? {
        guard let session,
              session.questions.indices.contains(questionIndex)
        else { return nil }
        return session.questions[questionIndex]
    }

    var progress: Double {
        guard let session, !session.questions.isEmpty else { return 0 }
        return Double(questionIndex + 1) / Double(session.questions.count)
    }

    func orderedEntries(currentLevel: String) -> [IOSExamEntry] {
        let normalized = Self.normalizedLevel(currentLevel)
        return IOSExamEntry.all.sorted { lhs, rhs in
            if lhs.level == normalized { return true }
            if rhs.level == normalized { return false }
            return lhs.level < rhs.level
        }
    }

    func start(level: String, language: String) async {
        guard phase != .loading && phase != .completing else { return }

        phase = .loading
        errorKey = nil
        self.language = Self.backendLanguage(language)

        do {
            let response = try await api.startExam(
                level: Self.normalizedLevel(level),
                language: self.language
            )
            guard response.ok,
                  let session = response.session,
                  !session.id.isEmpty,
                  !session.questions.isEmpty
            else {
                throw ExamViewModelError.invalidPayload
            }

            self.session = session
            questionIndex = 0
            selectedIndex = nil
            answers = [:]
            result = nil
            phase = .exam
            playCurrentAudioIfNeeded()
        } catch let error as APIError {
            phase = .center
            errorKey = Self.errorKey(error)
        } catch {
            phase = .center
            errorKey = "exam_start_error"
        }
    }

    func select(_ index: Int) {
        guard phase == .exam,
              selectedIndex == nil,
              let question = currentQuestion,
              question.options.indices.contains(index)
        else { return }
        selectedIndex = index
    }

    func advance() async {
        guard phase == .exam,
              let session,
              let question = currentQuestion,
              let selectedIndex
        else { return }

        answers[question.id] = selectedIndex
        speech.stop()

        if questionIndex < session.questions.count - 1 {
            questionIndex += 1
            self.selectedIndex = nil
            playCurrentAudioIfNeeded()
            return
        }

        phase = .completing
        errorKey = nil

        do {
            let completed = try await api.completeExam(
                session: session,
                language: language,
                answers: answers
            )
            guard completed.ok else {
                throw ExamViewModelError.invalidPayload
            }
            result = completed
            phase = .result
        } catch let error as APIError {
            phase = .exam
            errorKey = Self.errorKey(error)
        } catch {
            phase = .exam
            errorKey = "exam_save_error"
        }
    }

    func playCurrentAudio() {
        guard let question = currentQuestion else { return }
        let text = question.audioText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty { speech.play(text) }
    }

    func resetToCenter() {
        speech.stop()
        phase = .center
        session = nil
        questionIndex = 0
        selectedIndex = nil
        answers = [:]
        result = nil
        errorKey = nil
    }

    private func playCurrentAudioIfNeeded() {
        guard let question = currentQuestion,
              !question.audioText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return }
        speech.play(question.audioText)
    }

    private static func normalizedLevel(_ level: String) -> String {
        let value = level.lowercased()
        return ["hsk1", "hsk2", "hsk3", "hsk4"].contains(value) ? value : "hsk1"
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
            case "assistant_assessment_abandoned":
                return "exam_abandoned_error"
            default:
                return "exam_start_error"
            }
        case .transport:
            return "error_network"
        default:
            return "exam_start_error"
        }
    }

    deinit {
        Task { @MainActor [speech] in
            speech.stop()
        }
    }
}

enum ExamViewModelError: Error {
    case invalidPayload
}
