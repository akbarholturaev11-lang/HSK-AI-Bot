import Foundation

struct IOSExamStartRequest: Encodable, Sendable {
    let level: String
    let language: String
    let accessRef: String
    let adSupported: Bool
}

struct IOSExamStartResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let session: IOSExamSession?
}

struct IOSExamSession: Decodable, Sendable, Equatable {
    let id: String
    let level: String
    let durationMin: Int
    let passScore: Int
    let questions: [IOSExamQuestion]
}

struct IOSExamQuestion: Decodable, Sendable, Equatable, Identifiable {
    let id: String
    let format: String
    let section: String
    let prompt: String
    let sentence: String
    let audioText: String
    let options: [String]
}

struct IOSExamAnswer: Encodable, Sendable, Equatable {
    let questionId: String
    let selectedIndex: Int
}

struct IOSExamCompleteRequest: Encodable, Sendable {
    let sessionId: String
    let level: String
    let language: String
    let answers: [IOSExamAnswer]
}

struct IOSExamCompleteResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let duplicate: Bool
    let score: Int
    let total: Int
    let percent: Int
    let passScore: Int
    let passed: Bool
    let sectionScores: [String: IOSExamSectionScore]
    let wrongItems: [IOSPracticeWrong]
}

struct IOSExamSectionScore: Decodable, Sendable, Equatable {
    let score: Int
    let total: Int
    let percent: Int
}

struct IOSExamEntry: Sendable, Equatable, Identifiable {
    let level: String
    let questions: Int
    let minutes: Int
    let sections: [String]

    var id: String { level }

    static let all: [IOSExamEntry] = [
        IOSExamEntry(
            level: "hsk1",
            questions: 14,
            minutes: 25,
            sections: ["listening", "reading"]
        ),
        IOSExamEntry(
            level: "hsk2",
            questions: 12,
            minutes: 30,
            sections: ["listening", "reading"]
        ),
        IOSExamEntry(
            level: "hsk3",
            questions: 12,
            minutes: 35,
            sections: ["listening", "reading", "writing"]
        ),
        IOSExamEntry(
            level: "hsk4",
            questions: 12,
            minutes: 40,
            sections: ["listening", "reading", "writing"]
        ),
    ]
}
