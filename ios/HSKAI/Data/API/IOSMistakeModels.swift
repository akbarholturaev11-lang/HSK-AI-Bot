import Foundation

struct IOSMistakesOverviewResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let summary: IOSMistakeSummary
    let items: [IOSMistakeItem]
}

struct IOSMistakeSummary: Decodable, Sendable, Equatable {
    let total: Int
    let categories: [String: Int]
}

struct IOSMistakeItem: Decodable, Sendable, Equatable, Identifiable {
    let id: Int
    let category: String
    let source: String
    let level: String?
    let lesson: Int?
    let question: String
    let sentence: String
    let audioText: String
    let pinyin: String
    let userAnswer: String?
    let correctAnswer: String
    let explanation: String?
    let count: Int
}

struct IOSMistakeReviewStartRequest: Encodable, Sendable {
    let adSupported: Bool
    let accessRef: String
}

struct IOSMistakeReviewStartResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let session: IOSMistakeReviewSession?
}

struct IOSMistakeReviewSession: Decodable, Sendable, Equatable {
    let id: String
    let questions: [IOSMistakeReviewQuestion]
}

struct IOSMistakeReviewQuestion: Decodable, Sendable, Equatable, Identifiable {
    let id: String
    let category: String
    let prompt: String
    let options: [String]
    let sentence: String
    let audioText: String
    let pinyin: String
}

struct IOSMistakeReviewAnswerRequest: Encodable, Sendable {
    let sessionId: String
    let questionId: String
    let selectedIndex: Int
}

struct IOSMistakeReviewAnswerResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let questionId: String
    let selectedIndex: Int
    let correct: Bool
    let correctIndex: Int
    let correctAnswer: String
    let explanation: String
}

struct IOSMistakeReviewCompleteAnswer: Encodable, Sendable, Equatable {
    let questionId: String
    let selectedIndex: Int
}

struct IOSMistakeReviewCompleteRequest: Encodable, Sendable {
    let sessionId: String
    let answers: [IOSMistakeReviewCompleteAnswer]
}

struct IOSMistakeReviewCompleteResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let score: Int
    let total: Int
    let percent: Int
    let remaining: Int
}
