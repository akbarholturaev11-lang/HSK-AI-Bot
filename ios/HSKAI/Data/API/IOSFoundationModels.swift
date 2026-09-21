import Foundation

struct IOSFoundationResponse: Decodable, Sendable {
    let ok: Bool
    let foundation: IOSFoundationPayload
    let status: IOSCourseFoundation
}

struct IOSFoundationPayload: Decodable, Sendable {
    let id: String
    let version: Int
    let requiredObjectives: [String]
    let cards: [[String: JSONValue]]
}

struct IOSFoundationCompleteRequest: Encodable, Sendable {
    let foundationId: String
    let foundationVersion: Int
    let speakingBonus: Bool
    let eventId: String
}

struct IOSFoundationCompleteResponse: Decodable, Sendable {
    let ok: Bool
    let duplicate: Bool
    let foundation: IOSCourseFoundation
}

struct FoundationExample: Sendable, Equatable {
    let hanzi: String
    let pinyin: String
    let translation: String
}

struct FoundationObjective: Sendable, Equatable {
    let id: String
    let label: String
}

struct FoundationInfoCard: Sendable, Equatable {
    let id: String
    let type: String
    let title: String
    let text: String
    let audioText: String
    let naturalPinyin: String
    let examples: [FoundationExample]
    let objectives: [FoundationObjective]
}

struct FoundationChoiceCard: Sendable, Equatable {
    let id: String
    let objectiveId: String
    let title: String
    let prompt: String
    let audioText: String
    let options: [String]
    let correctIndex: Int
    let explanation: String
}

struct FoundationBuilderCard: Sendable, Equatable {
    let id: String
    let objectiveId: String
    let title: String
    let prompt: String
    let tokens: [String]
    let answerTokens: [String]
    let explanation: String
}

struct FoundationSpeakCard: Sendable, Equatable {
    let id: String
    let objectiveId: String
    let title: String
    let text: String
    let audioText: String
    let optional: Bool
    let example: FoundationExample?
}

enum FoundationCard: Sendable, Equatable {
    case info(FoundationInfoCard)
    case choice(FoundationChoiceCard)
    case builder(FoundationBuilderCard)
    case speak(FoundationSpeakCard)
    case result(FoundationInfoCard)
    case unsupported(id: String, type: String)
}

enum FoundationParser {
    static func parse(_ payload: IOSFoundationPayload, language: String) -> [FoundationCard] {
        payload.cards.map { card in
            let type = card.string("type").lowercased()
            let id = card.string("card_id")

            switch type {
            case "intro", "explain", "parts", "tones", "sandhi":
                return .info(infoCard(card, id: id, type: type, language: language))
            case "choice", "listen_choice":
                return .choice(
                    FoundationChoiceCard(
                        id: id,
                        objectiveId: card.string("objective_id"),
                        title: card.localized("title", language: language),
                        prompt: card.localized("prompt", language: language),
                        audioText: card.string("audio_text"),
                        options: localizedList(card["options"], language: language),
                        correctIndex: card.int("correct_index") ?? -1,
                        explanation: card.localized("explanation", language: language)
                    )
                )
            case "builder":
                return .builder(
                    FoundationBuilderCard(
                        id: id,
                        objectiveId: card.string("objective_id"),
                        title: card.localized("title", language: language),
                        prompt: card.localized("prompt", language: language),
                        tokens: stringList(card["tokens"]),
                        answerTokens: stringList(card["answer_tokens"]),
                        explanation: card.localized("explanation", language: language)
                    )
                )
            case "speak":
                return .speak(
                    FoundationSpeakCard(
                        id: id,
                        objectiveId: card.string("objective_id"),
                        title: card.localized("title", language: language),
                        text: card.localized("text", language: language),
                        audioText: card.string("audio_text"),
                        optional: card.bool("optional") ?? true,
                        example: example(card["example"], language: language)
                    )
                )
            case "result":
                return .result(infoCard(card, id: id, type: type, language: language))
            default:
                return .unsupported(id: id, type: type)
            }
        }
    }

    private static func infoCard(
        _ card: [String: JSONValue],
        id: String,
        type: String,
        language: String
    ) -> FoundationInfoCard {
        var examples = card.array("examples").compactMap {
            example($0, language: language)
        }
        if examples.isEmpty, let single = example(card["example"], language: language) {
            examples = [single]
        }

        let objectives = card.array("objectives").compactMap { raw -> FoundationObjective? in
            guard let object = raw.objectValue else { return nil }
            let objectiveId = object.string("objective_id")
            let label = object.localized("label", language: language)
            guard !objectiveId.isEmpty, !label.isEmpty else { return nil }
            return FoundationObjective(id: objectiveId, label: label)
        }

        return FoundationInfoCard(
            id: id,
            type: type,
            title: card.localized("title", language: language),
            text: card.localized("text", language: language),
            audioText: card.string("audio_text"),
            naturalPinyin: card.string("natural_pinyin"),
            examples: examples,
            objectives: objectives
        )
    }

    private static func example(
        _ value: JSONValue?,
        language: String
    ) -> FoundationExample? {
        guard let object = value?.objectValue else { return nil }
        let hanzi = object.string("zh")
        let pinyin = object.string("pinyin")
        let translation = object.localized("translation", language: language)
        guard !hanzi.isEmpty || !translation.isEmpty else { return nil }
        return FoundationExample(
            hanzi: hanzi,
            pinyin: pinyin,
            translation: translation
        )
    }

    private static func localizedList(
        _ value: JSONValue?,
        language: String
    ) -> [String] {
        value?.arrayValue?.map { $0.localized(language: language) } ?? []
    }

    private static func stringList(_ value: JSONValue?) -> [String] {
        value?.arrayValue?.compactMap(\.stringValue) ?? []
    }
}
