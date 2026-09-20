import Foundation

@MainActor
final class FoundationViewModel: ObservableObject {
    @Published private(set) var isLoading = true
    @Published private(set) var cards: [FoundationCard] = []
    @Published private(set) var cardIndex = 0
    @Published private(set) var requiredObjectives: Set<String> = []
    @Published private(set) var masteredObjectives: Set<String> = []
    @Published private(set) var selectedChoice: Int?
    @Published private(set) var builderTokens: [String] = []
    @Published private(set) var answerCorrect: Bool?
    @Published private(set) var isSaving = false
    @Published private(set) var isCompleted = false
    @Published private(set) var errorKey: String?

    private let api: IOSCourseAPI
    private let language: String
    private let speech = MandarinSpeechPlayer()
    private var eventId = "ios:foundation:\(UUID().uuidString.lowercased())"

    init(api: IOSCourseAPI, language: String) {
        self.api = api
        self.language = language
    }

    var currentCard: FoundationCard? {
        cards.indices.contains(cardIndex) ? cards[cardIndex] : nil
    }

    var progress: Double {
        guard !cards.isEmpty else { return 0 }
        return Double(cardIndex + 1) / Double(cards.count)
    }

    var canFinish: Bool {
        requiredObjectives.isSubset(of: masteredObjectives)
    }

    func load() async {
        isLoading = true
        errorKey = nil
        do {
            let response = try await api.foundation()
            let parsed = FoundationParser.parse(response.foundation, language: language)
            guard response.ok, !parsed.isEmpty else {
                throw FoundationViewModelError.invalidPayload
            }
            cards = parsed
            requiredObjectives = Set(response.foundation.requiredObjectives)
            masteredObjectives = []
            cardIndex = 0
            selectedChoice = nil
            builderTokens = []
            answerCorrect = nil
            isCompleted = response.status.completed
            eventId = "ios:foundation:\(UUID().uuidString.lowercased())"
            isLoading = false
        } catch let error as APIError where error.isSessionExpired {
            isLoading = false
            errorKey = "error_session_expired"
        } catch {
            isLoading = false
            errorKey = "foundation_load_error"
        }
    }

    func choose(_ index: Int) {
        guard case .choice(let card) = currentCard,
              card.options.indices.contains(index)
        else { return }

        selectedChoice = index
        let correct = index == card.correctIndex
        answerCorrect = correct
        if correct, !card.objectiveId.isEmpty {
            masteredObjectives.insert(card.objectiveId)
        }
    }

    func addBuilderToken(_ token: String) {
        guard case .builder(let card) = currentCard,
              card.tokens.contains(token),
              builderTokens.count < card.answerTokens.count
        else { return }

        builderTokens.append(token)
        answerCorrect = nil
    }

    func undoBuilderToken() {
        guard !builderTokens.isEmpty else { return }
        builderTokens.removeLast()
        answerCorrect = nil
    }

    func submitBuilder() {
        guard case .builder(let card) = currentCard,
              builderTokens.count == card.answerTokens.count
        else { return }

        let correct = builderTokens == card.answerTokens
        answerCorrect = correct
        if correct, !card.objectiveId.isEmpty {
            masteredObjectives.insert(card.objectiveId)
        }
    }

    func playCurrentAudio() {
        guard let currentCard else { return }
        switch currentCard {
        case .info(let card):
            speech.play(card.audioText.isEmpty ? card.examples.first?.hanzi ?? "" : card.audioText)
        case .choice(let card):
            speech.play(card.audioText)
        case .speak(let card):
            speech.play(card.audioText.isEmpty ? card.example?.hanzi ?? "" : card.audioText)
        case .builder:
            break
        case .result(let card):
            speech.play(card.audioText)
        case .unsupported:
            break
        }
    }

    func play(_ text: String) {
        speech.play(text)
    }

    func advance() async {
        guard let card = currentCard, !isSaving else { return }

        switch card {
        case .choice, .builder:
            guard answerCorrect == true else { return }
        case .result:
            guard canFinish else {
                errorKey = "foundation_objectives_missing"
                return
            }
            await finish()
            return
        case .info, .speak, .unsupported:
            break
        }

        guard cardIndex < cards.count - 1 else {
            if canFinish {
                await finish()
            }
            return
        }

        cardIndex += 1
        selectedChoice = nil
        builderTokens = []
        answerCorrect = nil
        errorKey = nil
    }

    func retryCurrent() {
        selectedChoice = nil
        builderTokens = []
        answerCorrect = nil
        errorKey = nil
    }

    private func finish() async {
        guard canFinish, !isSaving else { return }
        isSaving = true
        errorKey = nil

        do {
            let response = try await api.completeFoundation(
                speakingBonus: false,
                eventId: eventId
            )
            guard response.ok, response.foundation.completed else {
                throw FoundationViewModelError.invalidPayload
            }
            isCompleted = true
            isSaving = false
        } catch {
            isSaving = false
            errorKey = "foundation_save_error"
        }
    }

    deinit {
        Task { @MainActor [speech] in
            speech.stop()
        }
    }
}

enum FoundationViewModelError: Error {
    case invalidPayload
}
