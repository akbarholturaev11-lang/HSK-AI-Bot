import Foundation

struct IOSLessonResponse: Decodable, Sendable {
    let ok: Bool
    let level: String
    let lessonOrder: Int
    let previewHalf: Bool?
    let previewCardLimit: Int?
    let totalCards: Int?
    let completionAllowed: Bool?
    let completionError: String?
    let lesson: [String: JSONValue]
}

struct IOSCourseMistake: Encodable, Sendable, Equatable {
    let materialRef: String
    let selectedIndex: Int?
    let selectedAnswer: String?
    let selectedTokens: [String]?
    let selectedLeftIndex: Int?
    let selectedRightIndex: Int?

    init(
        materialRef: String,
        selectedIndex: Int? = nil,
        selectedAnswer: String? = nil,
        selectedTokens: [String]? = nil,
        selectedLeftIndex: Int? = nil,
        selectedRightIndex: Int? = nil
    ) {
        self.materialRef = materialRef
        self.selectedIndex = selectedIndex
        self.selectedAnswer = selectedAnswer
        self.selectedTokens = selectedTokens
        self.selectedLeftIndex = selectedLeftIndex
        self.selectedRightIndex = selectedRightIndex
    }
}

struct IOSCourseCompleteRequest: Encodable, Sendable {
    let lessonOrder: Int
    let eventId: String
    let mistakes: [IOSCourseMistake]
    let accessRef: String
}

struct IOSCourseCompleteResponse: Decodable, Sendable {
    let ok: Bool
    let completedLesson: Int?
    let nextLesson: Int?
    let completedLessonsCount: Int?
    let rankBefore: Int?
    let rankAfter: Int?
    let duplicate: Bool?
}

struct Lesson: Sendable, Equatable {
    let level: String
    let order: Int
    let sourceLesson: Int
    let part: Int
    let partCount: Int
    let isCheckpoint: Bool
    let title: String
    let subtitle: String
    let sections: [LessonSection]

    var cards: [LessonCard] { sections.flatMap(\.cards) }
}

struct LessonSection: Sendable, Equatable {
    let sectionNo: Int
    let title: String
    let purpose: String
    let cards: [LessonCard]
}

enum LessonChoiceKind: String, Sendable, Equatable {
    case meaning
    case translation
    case hanzi
    case pinyin
    case quickQuiz
    case gapFill
    case listening
    case dialogCloze
}

struct LessonDialogLine: Sendable, Equatable {
    let speaker: String
    let text: String
    let isBlank: Bool
}

struct LessonChoiceCard: Sendable, Equatable {
    let materialRef: String
    let kind: LessonChoiceKind
    let title: String
    let prompt: String
    let options: [String]
    let correctIndex: Int
    let explanation: String
    let sentence: String
    let audioText: String
    let audioPinyin: String
    let lines: [LessonDialogLine]
    let reviewOrigin: String

    var isReviewCard: Bool { !reviewOrigin.isEmpty }
}

struct LessonWordCard: Sendable, Equatable {
    let materialRef: String
    let number: Int
    let hanzi: String
    let pinyin: String
    let partOfSpeech: String
    let meaning: String
}

struct LessonGrammarExample: Sendable, Equatable {
    let hanzi: String
    let pinyin: String
    let translation: String
}

struct LessonGrammarCard: Sendable, Equatable {
    let materialRef: String
    let number: Int
    let title: String
    let titleZh: String
    let rule: String
    let examples: [LessonGrammarExample]
}

struct LessonPronunciationCard: Sendable, Equatable {
    let materialRef: String
    let phrase: String
    let pinyin: String
    let translation: String
}

struct LessonMatchPair: Sendable, Equatable {
    let hanzi: String
    let meaning: String
}

struct LessonMatchCard: Sendable, Equatable {
    let materialRef: String
    let pairs: [LessonMatchPair]
    let explanation: String
}

struct LessonBuilderCard: Sendable, Equatable {
    let materialRef: String
    let prompt: String
    let hanzi: String
    let pinyin: String
    let translation: String
    let tokens: [String]
    let answerTokens: [String]
    let explanation: String
    let reverse: Bool
}

enum LessonCard: Sendable, Equatable {
    case choice(LessonChoiceCard)
    case word(LessonWordCard)
    case grammar(LessonGrammarCard)
    case pronunciation(LessonPronunciationCard)
    case match(LessonMatchCard)
    case builder(LessonBuilderCard)
    case unsupported(materialRef: String, rawType: String)

    var materialRef: String {
        switch self {
        case .choice(let card): return card.materialRef
        case .word(let card): return card.materialRef
        case .grammar(let card): return card.materialRef
        case .pronunciation(let card): return card.materialRef
        case .match(let card): return card.materialRef
        case .builder(let card): return card.materialRef
        case .unsupported(let ref, _): return ref
        }
    }
}
