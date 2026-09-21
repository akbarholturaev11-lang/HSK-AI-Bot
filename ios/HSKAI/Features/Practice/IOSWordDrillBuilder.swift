import Foundation

struct IOSDrillQuestion: Sendable, Equatable, Identifiable {
    let hanzi: String
    let pinyin: String
    let meaning: String
    let options: [String]
    let isReview: Bool

    var id: String { hanzi }
}

enum IOSWordDrillBuilder {
    static let questionCount = 10

    static func pool(_ words: [IOSDictionaryWord]) -> [IOSDictionaryWord] {
        words.filter { $0.hanzi.count == 1 }
    }

    static func build(
        targets: [IOSDrillWord],
        pool: [IOSDictionaryWord],
        limit: Int = questionCount
    ) -> [IOSDrillQuestion] {
        let byHanzi = Dictionary(uniqueKeysWithValues: pool.map { ($0.hanzi, $0) })
        var picks: [(IOSDictionaryWord, Bool)] = []
        var used = Set<String>()

        for target in targets {
            guard let word = byHanzi[target.hanzi], used.insert(word.hanzi).inserted else {
                continue
            }
            picks.append((word, target.kind == "review"))
        }

        if picks.count < limit {
            for word in pool.shuffled() where !used.contains(word.hanzi) {
                guard picks.count < limit else { break }
                used.insert(word.hanzi)
                picks.append((word, false))
            }
        }

        return picks.prefix(limit).compactMap { word, isReview in
            let distractors = pool
                .filter { $0.hanzi != word.hanzi }
                .shuffled()
                .prefix(3)
            guard distractors.count == 3 else { return nil }
            let options = (Array(distractors) + [word]).shuffled().map(\.hanzi)
            return IOSDrillQuestion(
                hanzi: word.hanzi,
                pinyin: word.pinyin,
                meaning: word.meaning,
                options: options,
                isReview: isReview
            )
        }
    }
}
