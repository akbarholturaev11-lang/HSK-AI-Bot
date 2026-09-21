import Foundation

struct IOSPracticeStartRequest: Encodable, Sendable {
    let mode: String
    let level: String
    let language: String
    let skill: String
    let accessRef: String
    let adSupported: Bool
}

struct IOSPracticeStartResponse: Decodable, Sendable {
    let ok: Bool
    let session: IOSPracticeSession?
}

struct IOSPracticeSession: Decodable, Sendable, Equatable {
    let id: String
    let mode: String
    let skill: String
    let level: String
    let questions: [IOSPracticeQuestion]
}

struct IOSPracticeQuestion: Decodable, Sendable, Equatable, Identifiable {
    let id: String
    let level: String
    let lesson: Int
    let type: String
    let subtype: String
    let prompt: String
    let sentence: String
    let audioText: String
    let pinyin: String
    let options: [String]
    let answerIndex: Int
    let explanation: String
}

struct IOSPracticeAnswer: Encodable, Sendable, Equatable {
    let questionId: String
    let selected: Int
}

struct IOSPracticeCompleteRequest: Encodable, Sendable {
    let mode: String
    let level: String
    let language: String
    let skill: String
    let sessionId: String
    let answers: [IOSPracticeAnswer]
    let accessRef: String
    let adSupported: Bool
}

struct IOSPracticeCompleteResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let score: Int
    let total: Int
    let percent: Int
    let recommendation: String
    let wrongItems: [IOSPracticeWrong]
}

struct IOSPracticeWrong: Decodable, Sendable, Equatable, Identifiable {
    let question: String
    let selectedAnswer: String
    let correctAnswer: String
    let explanation: String
    let pinyin: String

    var id: String {
        [question, selectedAnswer, correctAnswer].joined(separator: "|")
    }
}
