import Foundation

@MainActor
final class WordDrillViewModel: ObservableObject {
    enum Phase: Equatable { case idle, loading, running, finished }

    @Published private(set) var phase: Phase = .idle
    @Published private(set) var questions: [IOSDrillQuestion] = []
    @Published private(set) var index = 0
    @Published private(set) var selected: String?
    @Published private(set) var answered = false
    @Published private(set) var wasCorrect = false
    @Published private(set) var correctCount = 0
    @Published private(set) var errorKey: String?
    @Published private(set) var limitReached = false

    private let practiceAPI: IOSPracticeAPI
    private let courseAPI: IOSCourseAPI
    private var feature = "recognition"
    private var level = "hsk1"
    private var language = "ru"
    private var mistakes: [IOSDrillMistake] = []
    private var results: [IOSDrillResult] = []
    private var accessAttemptRef = ""

    init(practiceAPI: IOSPracticeAPI, courseAPI: IOSCourseAPI) {
        self.practiceAPI = practiceAPI
        self.courseAPI = courseAPI
    }

    var current: IOSDrillQuestion? {
        questions.indices.contains(index) ? questions[index] : nil
    }

    var progress: Double {
        guard !questions.isEmpty else { return 0 }
        return Double(index) / Double(questions.count)
    }

    func startRecognition(level: String, language: String) async {
        guard phase != .loading else { return }
        feature = "recognition"
        self.level = Self.normalizedLevel(level)
        self.language = Self.backendLanguage(language)
        accessAttemptRef = "drill:\(UUID().uuidString.lowercased())"
        mistakes = []
        results = []
        phase = .loading
        errorKey = nil
        limitReached = false

        do {
            let gate = try await practiceAPI.drillGate(
                feature: feature,
                ref: accessAttemptRef
            )
            guard gate.ok, gate.allowed else {
                limitReached = true
                phase = .idle
                return
            }

            async let dictionary = courseAPI.dictionary()
            async let advised = practiceAPI.drillWords(
                feature: feature,
                limit: IOSWordDrillBuilder.questionCount
            )
            let dictionaryPayload = try await dictionary
            guard dictionaryPayload.ok else { throw WordDrillError.invalidPayload }
            let pool = IOSWordDrillBuilder.pool(dictionaryPayload.words)
            guard pool.count >= 8 else { throw WordDrillError.invalidPayload }

            let targets = (try? await advised)?.words ?? []
            let built = IOSWordDrillBuilder.build(targets: targets, pool: pool)
            guard !built.isEmpty else { throw WordDrillError.invalidPayload }

            questions = built
            index = 0
            selected = nil
            answered = false
            wasCorrect = false
            correctCount = 0
            phase = .running
        } catch let error as APIError {
            phase = .idle
            if case .httpStatus(let status, _) = error, status == 403 {
                limitReached = true
            } else {
                errorKey = "drill_load_error"
            }
        } catch {
            phase = .idle
            errorKey = "drill_load_error"
        }
    }

    func choose(_ option: String) {
        guard phase == .running, !answered, let current,
              current.options.contains(option) else { return }
        let correct = option == current.hanzi
        selected = option
        answered = true
        wasCorrect = correct
        results.append(IOSDrillResult(hanzi: current.hanzi, correct: correct))
        if correct {
            correctCount += 1
        } else {
            mistakes.append(IOSDrillMistake(hanzi: current.hanzi, selected: option))
        }
    }

    func advance() async {
        guard phase == .running, answered else { return }
        if index + 1 < questions.count {
            index += 1
            selected = nil
            answered = false
            wasCorrect = false
            return
        }

        phase = .finished
        guard !mistakes.isEmpty || !results.isEmpty else { return }
        _ = try? await practiceAPI.reportDrill(
            feature: feature,
            level: level,
            language: language,
            mistakes: mistakes,
            results: results
        )
    }

    func reset() {
        phase = .idle
        questions = []
        index = 0
        selected = nil
        answered = false
        wasCorrect = false
        correctCount = 0
        errorKey = nil
        limitReached = false
        mistakes = []
        results = []
        accessAttemptRef = ""
    }

    private static func normalizedLevel(_ level: String) -> String {
        let clean = level.lowercased()
        return ["hsk1", "hsk2", "hsk3", "hsk4"].contains(clean) ? clean : "hsk1"
    }

    private static func backendLanguage(_ language: String) -> String {
        switch language.lowercased() {
        case "uz": return "uz"
        case "tj", "tg": return "tj"
        default: return "ru"
        }
    }
}

enum WordDrillError: Error { case invalidPayload }
