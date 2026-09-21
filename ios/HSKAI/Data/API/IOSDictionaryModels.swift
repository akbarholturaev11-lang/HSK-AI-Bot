import Foundation

struct IOSDictionaryResponse: Decodable, Sendable, Equatable {
    let ok: Bool
    let version: String
    let language: String
    let words: [IOSDictionaryWord]
}

struct IOSDictionaryWord: Decodable, Sendable, Equatable, Identifiable {
    let hanzi: String
    let pinyin: String
    let meaning: String
    let level: String

    var id: String { "\(level):\(hanzi):\(pinyin)" }

    enum CodingKeys: String, CodingKey {
        case hanzi = "h"
        case pinyin = "p"
        case meaning = "m"
        case level = "lv"
    }
}
