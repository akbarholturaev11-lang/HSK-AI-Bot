import Foundation

@MainActor
final class LessonViewModel: ObservableObject {
    struct CompletionSummary: Equatable {
        let correct: Int
        let graded: Int
        let duplicate: Bool
        let rankBefore: Int
        let rankAfter: Int
    }

    enum Outcome: Equatable {
        case inProgress
        case previewEnded
        case completed(CompletionSummary)
        case failed
    }

    @Published private(set) var isLoading = true
    @Published private(set) var lesson: Lesson?
    @Published private(set) var cardIndex = 0
    @Published private(set) var selectedChoice: Int?
    @Published private(set) var builderTokens: [String] = []
    @Published private(set) var answerCorrect: Bool?
    @Published private(set) var answerExplanation = ""
    @Published private(set) var correctCount = 0
    @Published private(set) var gradedAnswered = 0
    @Published private(set) var hearts = 5
    @Published private(set) var completionAllowed = false
    @Published private(set) var previewCardLimit = 0
    @Published private(set) var isSubmitting = false
    @Published private(set) var errorKey: String?
    @Published private(set) var outcome: Outcome = .inProgress

    @Published private(set) var selectedMatchLeft: Int?
    @Published private(set) var selectedMatchRight: Int?
    @Published private(set) var matchedPairIndices: Set<Int> = []
    private var wrongMatchAttempts: [(Int, Int)] = []

    private let api: IOSCourseAPI
    let lessonOrder: Int
    private let language: String
    private let accessRef: String
    private let speech = MandarinSpeechPlayer()
    private var mistakes: [IOSCourseMistake] = []
    private let eventId = "ios:lesson:\(UUID().uuidString.lowercased())"

    init(
        api: IOSCourseAPI,
        lessonOrder: Int,
        language: String,
        accessRef: String = ""
    ) {
        self.api = api
        self.lessonOrder = lessonOrder
        self.language = language
        self.accessRef = accessRef
    }

    var cards: [LessonCard] { lesson?.cards ?? [] }

    var currentCard: LessonCard? {
        cards.indices.contains(cardIndex) ? cards[cardIndex] : nil
    }

    var progress: Double {
        guard !cards.isEmpty else { return 0 }
        return Double(cardIndex) / Double(cards.count)
    }

    var sectionTitle: String {
        guard let lesson else { return "" }
        var cursor = 0
        for section in lesson.sections {
            let end = cursor + section.cards.count
            if cardIndex < end { return section.title }
            cursor = end
        }
        return ""
    }

    func load() async {
        isLoading = true
        errorKey = nil
        do {
            let response = try await api.lesson(
                order: lessonOrder,
                accessRef: accessRef
            )
            guard response.ok else {
                throw LessonViewModelError.invalidPayload
            }

            let parsed = IOSLessonParser.parse(
                response: response,
                language: language
            )
            guard !parsed.cards.isEmpty else {
                throw LessonViewModelError.invalidPayload
            }

            lesson = parsed
            completionAllowed = response.completionAllowed ?? false
            previewCardLimit = response.previewCardLimit ?? 0
            cardIndex = 0
            selectedChoice = nil
            builderTokens = []
            answerCorrect = nil
            answerExplanation = ""
            correctCount = 0
            gradedAnswered = 0
            hearts = 5
            mistakes = []
            resetMatch()
            outcome = .inProgress
            isLoading = false
        } catch let error as APIError where error.isSessionExpired {
            isLoading = false
            errorKey = "error_session_expired"
        } catch let error as APIError {
            isLoading = false
            switch error {
            case .server(let code, _):
                errorKey = code == "android_foundation_required"
                    ? "foundation_gate_title"
                    : "lesson_load_error"
            default:
                errorKey = "lesson_load_error"
            }
        } catch {
            isLoading = false
            errorKey = "lesson_load_error"
        }
    }

    func answerChoice(_ index: Int) {
        guard answerCorrect == nil,
              case .choice(let card) = currentCard,
              card.options.indices.contains(index)
        else { return }

        selectedChoice = index
        let correct = index == card.correctIndex
        if !correct {
            addMistake(
                IOSCourseMistake(
                    materialRef: card.materialRef,
                    selectedIndex: index
                )
            )
        }
        record(correct: correct, explanation: card.explanation)
    }

    func addBuilderToken(_ token: String) {
        guard answerCorrect == nil,
              case .builder(let card) = currentCard,
              card.tokens.contains(token),
              builderTokens.count < card.answerTokens.count
        else { return }

        builderTokens.append(token)
    }

    func undoBuilderToken() {
        guard answerCorrect == nil, !builderTokens.isEmpty else { return }
        builderTokens.removeLast()
    }

    func submitBuilder() {
        guard answerCorrect == nil,
              case .builder(let card) = currentCard,
              builderTokens.count == card.answerTokens.count
        else { return }

        let correct = builderTokens == card.answerTokens
        if !correct {
            addMistake(
                IOSCourseMistake(
                    materialRef: card.materialRef,
                    selectedTokens: builderTokens
                )
            )
        }
        record(correct: correct, explanation: card.explanation)
    }

    func selectMatchLeft(_ index: Int) {
        guard answerCorrect == nil,
              case .match(let card) = currentCard,
              card.pairs.indices.contains(index),
              !matchedPairIndices.contains(index)
        else { return }

        selectedMatchLeft = index
        evaluateMatchIfReady()
    }

    func selectMatchRight(_ originalIndex: Int) {
        guard answerCorrect == nil,
              case .match(let card) = currentCard,
              card.pairs.indices.contains(originalIndex),
              !matchedPairIndices.contains(originalIndex)
        else { return }

        selectedMatchRight = originalIndex
        evaluateMatchIfReady()
    }

    func play(_ text: String) {
        speech.play(text)
    }

    func acknowledge() async {
        guard answerCorrect == nil else { return }
        await advance()
    }

    func advance() async {
        guard !isSubmitting else { return }

        if isCurrentCardGraded, answerCorrect == nil {
            return
        }

        let next = cardIndex + 1
        if !completionAllowed,
           previewCardLimit > 0,
           next >= min(previewCardLimit, cards.count) {
            outcome = .previewEnded
            return
        }

        if next >= cards.count {
            await finish()
            return
        }

        cardIndex = next
        selectedChoice = nil
        builderTokens = []
        answerCorrect = nil
        answerExplanation = ""
        resetMatch()
    }

    func retryCompletion() async {
        outcome = .inProgress
        await finish()
    }

    private var isCurrentCardGraded: Bool {
        guard let currentCard else { return false }
        switch currentCard {
        case .choice, .builder, .match:
            return true
        case .word, .grammar, .pronunciation, .unsupported:
            return false
        }
    }

    private func evaluateMatchIfReady() {
        guard let left = selectedMatchLeft,
              let right = selectedMatchRight,
              case .match(let card) = currentCard
        else { return }

        if left == right {
            matchedPairIndices.insert(left)
        } else {
            wrongMatchAttempts.append((left, right))
        }

        selectedMatchLeft = nil
        selectedMatchRight = nil

        if matchedPairIndices.count == card.pairs.count {
            for (leftIndex, rightIndex) in wrongMatchAttempts.prefix(50) {
                addMistake(
                    IOSCourseMistake(
                        materialRef: card.materialRef,
                        selectedLeftIndex: leftIndex,
                        selectedRightIndex: rightIndex
                    )
                )
            }
            record(
                correct: wrongMatchAttempts.isEmpty,
                explanation: card.explanation
            )
        }
    }

    private func record(correct: Bool, explanation: String) {
        answerCorrect = correct
        answerExplanation = explanation
        gradedAnswered += 1
        if correct {
            correctCount += 1
        } else {
            hearts = max(0, hearts - 1)
        }
    }

    private func addMistake(_ mistake: IOSCourseMistake) {
        guard mistakes.count < 50 else { return }
        mistakes.append(mistake)
    }

    private func resetMatch() {
        selectedMatchLeft = nil
        selectedMatchRight = nil
        matchedPairIndices = []
        wrongMatchAttempts = []
    }

    private func finish() async {
        guard completionAllowed else {
            outcome = .previewEnded
            return
        }
        guard !isSubmitting else { return }

        isSubmitting = true
        errorKey = nil
        do {
            let response = try await api.completeLesson(
                order: lessonOrder,
                eventId: eventId,
                mistakes: mistakes,
                accessRef: accessRef
            )
            guard response.ok else {
                throw LessonViewModelError.invalidPayload
            }
            isSubmitting = false
            outcome = .completed(
                CompletionSummary(
                    correct: correctCount,
                    graded: gradedAnswered,
                    duplicate: response.duplicate ?? false,
                    rankBefore: response.rankBefore ?? 0,
                    rankAfter: response.rankAfter ?? 0
                )
            )
        } catch {
            isSubmitting = false
            errorKey = "lesson_save_error"
            outcome = .failed
        }
    }

    deinit {
        Task { @MainActor [speech] in
            speech.stop()
        }
    }
}

enum LessonViewModelError: Error {
    case invalidPayload
}
