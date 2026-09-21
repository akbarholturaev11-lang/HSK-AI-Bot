import Foundation

struct IOSDrillGateRequest: Encodable, Sendable {
    let feature: String
    let ref: String
    let accessRef: String
}

struct IOSDrillGateResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let allowed: Bool
    let isPaid: Bool
    let remaining: Int?
    let resetAt: String?
}

struct IOSDrillWordsRequest: Encodable, Sendable {
    let feature: String
    let limit: Int
}

struct IOSDrillWordsResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let skill: String
    let day: String
    let words: [IOSDrillWord]
}

struct IOSDrillWord: Decodable, Sendable, Equatable {
    let hanzi: String
    let kind: String
    let box: Int

    enum CodingKeys: String, CodingKey {
        case hanzi = "zh"
        case kind, box
    }
}

struct IOSDrillMistake: Encodable, Sendable, Equatable {
    let hanzi: String
    let selected: String
}

struct IOSDrillResult: Encodable, Sendable, Equatable {
    let hanzi: String
    let correct: Bool
}

struct IOSDrillReportRequest: Encodable, Sendable {
    let feature: String
    let level: String
    let language: String
    let mistakes: [IOSDrillMistake]
    let results: [IOSDrillResult]
}

struct IOSDrillReportResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let recorded: Int
    let scheduled: Int
}
