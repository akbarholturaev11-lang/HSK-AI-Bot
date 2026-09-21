import Foundation

@MainActor
final class MistakesViewModel: ObservableObject {
    enum Phase: Equatable {
        case overview
        case loadingReview
        case review
        case completing
        case result
    }

    @Published private(set) var phase: Phase = .overview
    @Published private(set) var overview: IOSMistakesOverviewResponse?
    @Published private(set) var isLoadingOverview = false
    @Published private(set) var reviewSession: IOSMistakeReviewSession?
    @Published private(set) var questionIndex = 0
    @Published private(set) var selectedIndex: Int?
    @Published private(set) var feedback: IOSMistakeReviewAnswerResponse?
    @Published private(set) var answers: [String: Int] = [:]
    @Published private(set) var result: IOSMistakeReviewCompleteResponse?
    @Published private(set) var errorKey: String?

    private let api: IOSPracticeAPI
    private let speech = MandarinSpeechPlayer()

    init(api: IOSPracticeAPI) {
        self.api = api
    }

    var currentQuestion: IOSMistakeReviewQuestion? {
        guard let reviewSession,
              reviewSession.questions.indices.contains(questionIndex)
        else { return nil }
        return reviewSession.questions[questionIndex]
    }

    var progress: Double {
        guard let reviewSession, !reviewSession.questions.isEmpty else { return 0 }
        return Double(questionIndex + 1) / Double(reviewSession.questions.count)
    }

    func loadOverview(force: Bool = false) async {
        guard !isLoadingOverview else { return }
        if !force, overview != nil { return }

        isLoadingOverview = true
        errorKey = nil
        do {
            var allItems: [IOSMistakeItem] = []
            var summary: IOSMistakeSummary?
            var offset = 0

            while offset < 500 {
                let page = try await api.mistakes(limit: 100, offset: offset)
                guard page.ok else { throw MistakesViewModelError.invalidPayload }
                if summary == nil { summary = page.summary }
                allItems.append(contentsOf: page.items)
                if page.items.count < 100 { break }
                offset += page.items.count
            }

            overview = IOSMistakesOverviewResponse(
                ok: true,
                summary: summary ?? IOSMistakeSummary(total: 0, categories: [:]),
                items: allItems
            )
            isLoadingOverview = false
        } catch let error as APIError where error.isSessionExpired {
            isLoadingOverview = false
            errorKey = "error_session_expired"
        } catch {
            isLoadingOverview = false
            errorKey = "mistakes_load_error"
        }
    }

    func startReview() async {
        guard phase == .overview else { return }
        phase = .loadingReview
        errorKey = nil
        do {
            let response = try await api.startMistakeReview()
            guard response.ok,
                  let session = response.session,
                  !session.id.isEmpty,
                  !session.questions.isEmpty
            else {
                throw MistakesViewModelError.emptyReview
            }

            reviewSession = session
            questionIndex = 0
            selectedIndex = nil
            feedback = nil
            answers = [:]
            result = nil
            phase = .review
        } catch let error as APIError {
            phase = .overview
            switch error {
            case .server(let code, _) where code == "mistake_review_empty":
                errorKey = "mistakes_review_empty"
            case .server(let code, _) where code == "free_feature_limit_reached":
                errorKey = "practice_limit_error"
            case .transport:
                errorKey = "error_network"
            default:
                errorKey = "mistakes_review_error"
            }
        } catch MistakesViewModelError.emptyReview {
            phase = .overview
            errorKey = "mistakes_review_empty"
        } catch {
            phase = .overview
            errorKey = "mistakes_review_error"
        }
    }

    func answer(_ index: Int) async {
        guard phase == .review,
              feedback == nil,
              selectedIndex == nil,
              let session = reviewSession,
              let question = currentQuestion,
              question.options.indices.contains(index)
        else { return }

        selectedIndex = index
        errorKey = nil
        do {
            let serverFeedback = try await api.answerMistakeReview(
                sessionId: session.id,
                questionId: question.id,
                selectedIndex: index
            )
            guard serverFeedback.ok else {
                throw MistakesViewModelError.invalidPayload
            }
            answers[question.id] = index
            feedback = serverFeedback
        } catch {
            selectedIndex = nil
            errorKey = "mistakes_review_error"
        }
    }

    func advance() async {
        guard phase == .review,
              feedback != nil,
              let session = reviewSession
        else { return }

        if questionIndex < session.questions.count - 1 {
            questionIndex += 1
            selectedIndex = nil
            feedback = nil
            errorKey = nil
            return
        }

        phase = .completing
        errorKey = nil
        do {
            let completed = try await api.completeMistakeReview(
                sessionId: session.id,
                answers: answers,
                questions: session.questions
            )
            guard completed.ok else {
                throw MistakesViewModelError.invalidPayload
            }
            result = completed
            phase = .result
        } catch {
            phase = .review
            errorKey = "mistakes_review_save_error"
        }
    }

    func playCurrentAudio() {
        guard let question = currentQuestion else { return }
        let text = question.audioText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty { speech.play(text) }
    }

    func finishResult() async {
        reviewSession = nil
        questionIndex = 0
        selectedIndex = nil
        feedback = nil
        answers = [:]
        result = nil
        phase = .overview
        overview = nil
        await loadOverview(force: true)
    }

    func reset() {
        speech.stop()
        phase = .overview
        reviewSession = nil
        questionIndex = 0
        selectedIndex = nil
        feedback = nil
        answers = [:]
        result = nil
        errorKey = nil
    }

    deinit {
        Task { @MainActor [speech] in
            speech.stop()
        }
    }
}

enum MistakesViewModelError: Error {
    case invalidPayload
    case emptyReview
}
