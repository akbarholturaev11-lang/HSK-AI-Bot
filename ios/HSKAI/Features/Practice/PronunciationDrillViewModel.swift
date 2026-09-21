import Foundation

@MainActor
final class PronunciationDrillViewModel: ObservableObject {
    enum Phase: Equatable { case idle, loading, running, finished }

    @Published private(set) var phase: Phase = .idle
    @Published private(set) var questions: [IOSDrillQuestion] = []
    @Published private(set) var index = 0
    @Published private(set) var answered = false
    @Published private(set) var wasCorrect = false
    @Published private(set) var correctCount = 0
    @Published private(set) var spokenScore: Int?
    @Published private(set) var isRecording = false
    @Published private(set) var isScoring = false
    @Published private(set) var limitReached = false
    @Published private(set) var permissionDenied = false
    @Published private(set) var errorKey: String?

    private let practiceAPI: IOSPracticeAPI
    private let courseAPI: IOSCourseAPI
    private let recorder: MandarinAudioRecorder
    private let speech = MandarinSpeechPlayer()
    private var level = "hsk1"
    private var language = "ru"
    private var results: [IOSDrillResult] = []
    private var accessAttemptRef = ""

    init(
        practiceAPI: IOSPracticeAPI,
        courseAPI: IOSCourseAPI,
        recorder: MandarinAudioRecorder = MandarinAudioRecorder()
    ) {
        self.practiceAPI = practiceAPI
        self.courseAPI = courseAPI
        self.recorder = recorder
    }

    var current: IOSDrillQuestion? {
        questions.indices.contains(index) ? questions[index] : nil
    }

    var progress: Double {
        guard !questions.isEmpty else { return 0 }
        return Double(index) / Double(questions.count)
    }

    func start(level: String, language: String) async {
        guard phase != .loading else { return }
        self.level = Self.normalizedLevel(level)
        self.language = Self.backendLanguage(language)
        accessAttemptRef = "drill:\(UUID().uuidString.lowercased())"
        results = []
        phase = .loading
        errorKey = nil
        limitReached = false
        permissionDenied = false

        do {
            let gate = try await practiceAPI.drillGate(
                feature: "pronunciation",
                ref: accessAttemptRef
            )
            guard gate.ok, gate.allowed else {
                limitReached = true
                phase = .idle
                return
            }

            async let dictionary = courseAPI.dictionary()
            async let advised = practiceAPI.drillWords(
                feature: "pronunciation",
                limit: IOSWordDrillBuilder.questionCount
            )
            let dictionaryPayload = try await dictionary
            guard dictionaryPayload.ok else { throw PronunciationDrillError.invalidPayload }
            let pool = IOSWordDrillBuilder.pool(dictionaryPayload.words)
            guard pool.count >= 8 else { throw PronunciationDrillError.invalidPayload }
            let targets = (try? await advised)?.words ?? []
            let built = IOSWordDrillBuilder.build(targets: targets, pool: pool)
            guard !built.isEmpty else { throw PronunciationDrillError.invalidPayload }

            questions = built
            index = 0
            answered = false
            wasCorrect = false
            correctCount = 0
            spokenScore = nil
            phase = .running
        } catch let error as APIError {
            phase = .idle
            if case .httpStatus(let status) = error, status == 403 {
                limitReached = true
            } else {
                errorKey = "drill_load_error"
            }
        } catch {
            phase = .idle
            errorKey = "drill_load_error"
        }
    }

    func playCurrent() {
        guard let current else { return }
        speech.play(current.hanzi)
    }

    func speak() async {
        guard phase == .running, !answered, !isRecording, !isScoring,
              let current else { return }

        let allowed = await recorder.requestPermission()
        guard allowed else {
            permissionDenied = true
            errorKey = "pronunciation_permission_denied"
            return
        }

        do {
            permissionDenied = false
            errorKey = nil
            try recorder.start()
            isRecording = true
            try await Task.sleep(for: .milliseconds(2600))
            let audioDataURL = try recorder.stopDataURL()
            isRecording = false
            isScoring = true

            let response = try await practiceAPI.scorePronunciation(
                target: current.hanzi,
                targetPinyin: current.pinyin,
                language: language,
                level: level,
                audioDataUrl: audioDataURL
            )
            let passed = response.ok && response.score >= 60
            spokenScore = response.score
            wasCorrect = passed
            answered = true
            isScoring = false
            results.append(IOSDrillResult(hanzi: current.hanzi, correct: passed))
            if passed { correctCount += 1 }
        } catch is CancellationError {
            recorder.cancel()
            isRecording = false
            isScoring = false
        } catch {
            recorder.cancel()
            isRecording = false
            isScoring = false
            errorKey = "pronunciation_score_error"
        }
    }

    func skip() async {
        guard phase == .running, !isScoring else { return }
        recorder.cancel()
        isRecording = false
        await moveNext(reportAtEnd: true)
    }

    func advance() async {
        guard phase == .running, answered else { return }
        await moveNext(reportAtEnd: true)
    }

    private func moveNext(reportAtEnd: Bool) async {
        if index + 1 < questions.count {
            index += 1
            answered = false
            wasCorrect = false
            spokenScore = nil
            errorKey = nil
            return
        }
        phase = .finished
        guard reportAtEnd, !results.isEmpty else { return }
        _ = try? await practiceAPI.reportDrill(
            feature: "pronunciation",
            level: level,
            language: language,
            mistakes: [],
            results: results
        )
    }

    func reset() {
        recorder.cancel()
        speech.stop()
        phase = .idle
        questions = []
        index = 0
        answered = false
        wasCorrect = false
        correctCount = 0
        spokenScore = nil
        isRecording = false
        isScoring = false
        limitReached = false
        permissionDenied = false
        errorKey = nil
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

enum PronunciationDrillError: Error { case invalidPayload }
