import Foundation

enum IOSLessonParser {
    private static let exitTicketSectionNo = 99

    static func materialRef(
        level: String,
        lessonOrder: Int,
        sectionNo: Int,
        cardNo: Int
    ) -> String {
        "lesson:\(level):\(lessonOrder):section:\(sectionNo):card:\(cardNo)"
    }

    static func parse(
        response: IOSLessonResponse,
        language: String
    ) -> Lesson {
        let payload = response.lesson
        var parsedSections = payload.array("sections").enumerated().compactMap {
            index, element -> LessonSection? in
            guard let section = element.objectValue else { return nil }
            let sectionNo = section.int("section_no") ?? index + 1
            return LessonSection(
                sectionNo: sectionNo,
                title: section.localized("section_title", language: language),
                purpose: section.string("section_purpose"),
                cards: section.array("cards").enumerated().compactMap {
                    cardIndex, raw -> LessonCard? in
                    guard let card = raw.objectValue else { return nil }
                    return parseCard(
                        card,
                        language: language,
                        ref: materialRef(
                            level: response.level,
                            lessonOrder: response.lessonOrder,
                            sectionNo: sectionNo,
                            cardNo: cardIndex + 1
                        )
                    )
                }
            )
        }

        if let exitTicket = payload.object("exit_ticket") {
            let rawCards = exitTicket.array("cards")
            let cards = rawCards.enumerated().compactMap {
                index, raw -> LessonCard? in
                guard let card = raw.objectValue else { return nil }
                let ref = materialRef(
                    level: response.level,
                    lessonOrder: response.lessonOrder,
                    sectionNo: exitTicketSectionNo,
                    cardNo: index + 1
                )
                switch card.string("type").lowercased() {
                case "choice":
                    return choiceCard(
                        card,
                        kind: .meaning,
                        language: language,
                        ref: ref
                    )
                case "listen_choice":
                    return choiceCard(
                        card,
                        kind: .listening,
                        language: language,
                        ref: ref
                    )
                case "builder":
                    return .builder(
                        LessonBuilderCard(
                            materialRef: ref,
                            prompt: card.localized("prompt", language: language),
                            hanzi: "",
                            pinyin: "",
                            translation: "",
                            tokens: tokens(card["tokens"], language: language),
                            answerTokens: tokens(card["answer_tokens"], language: language),
                            explanation: card.localized("explanation", language: language),
                            reverse: false
                        )
                    )
                default:
                    return nil
                }
            }

            if !cards.isEmpty {
                parsedSections.append(
                    LessonSection(
                        sectionNo: exitTicketSectionNo,
                        title: rawCards.first?.objectValue?.localized(
                            "title",
                            language: language
                        ) ?? "",
                        purpose: "exit_ticket",
                        cards: cards
                    )
                )
            }
        }

        return Lesson(
            level: response.level,
            order: response.lessonOrder,
            sourceLesson: payload.int("source_lesson") ?? 0,
            part: payload.int("part_no") ?? 0,
            partCount: payload.int("part_count") ?? 0,
            isCheckpoint: payload.bool("checkpoint") ?? false,
            title: payload["title"]?.localized(language: language) ?? "",
            subtitle: payload.localized("subtitle", language: language),
            sections: parsedSections
        )
    }

    private static func parseCard(
        _ card: [String: JSONValue],
        language: String,
        ref: String
    ) -> LessonCard {
        let type = card.string("type").lowercased()
        if let kind = choiceKind(type) {
            return choiceCard(
                card,
                kind: kind,
                language: language,
                ref: ref
            )
        }

        switch type {
        case "active_word":
            guard let word = card.object("word") else {
                return .unsupported(materialRef: ref, rawType: type)
            }
            return .word(
                LessonWordCard(
                    materialRef: ref,
                    number: word.int("no") ?? 0,
                    hanzi: word.string("zh"),
                    pinyin: word.string("pinyin"),
                    partOfSpeech: word.string("pos"),
                    meaning: word.localized("meaning", language: language)
                )
            )

        case "_grammar":
            guard let grammar = card.object("g") else {
                return .unsupported(materialRef: ref, rawType: type)
            }
            let examples = grammar.array("examples").compactMap {
                raw -> LessonGrammarExample? in
                guard let item = raw.objectValue else { return nil }
                return LessonGrammarExample(
                    hanzi: item.string("zh"),
                    pinyin: item.string("pinyin"),
                    translation: item.localized("translation", language: language)
                )
            }
            return .grammar(
                LessonGrammarCard(
                    materialRef: ref,
                    number: grammar.int("no") ?? 0,
                    title: grammar.localized("title", language: language),
                    titleZh: grammar.string("title_zh"),
                    rule: grammar.localized("rule", language: language),
                    examples: examples
                )
            )

        case "pronunciation":
            return .pronunciation(
                LessonPronunciationCard(
                    materialRef: ref,
                    phrase: card.string("phrase"),
                    pinyin: card.string("pinyin"),
                    translation: card.localized("translation", language: language)
                )
            )

        case "match_pairs":
            let pairs = card.array("pairs").compactMap {
                raw -> LessonMatchPair? in
                guard let pair = raw.arrayValue, pair.count >= 2 else { return nil }
                let hanzi = pair[0].stringValue ?? ""
                let meaning = pair[1].localized(language: language)
                guard !hanzi.isEmpty, !meaning.isEmpty else { return nil }
                return LessonMatchPair(hanzi: hanzi, meaning: meaning)
            }
            return .match(
                LessonMatchCard(
                    materialRef: ref,
                    pairs: pairs,
                    explanation: card.localized("explanation", language: language)
                )
            )

        case "sentence_builder":
            return .builder(
                LessonBuilderCard(
                    materialRef: ref,
                    prompt: card.localized("sentence", language: language),
                    hanzi: "",
                    pinyin: "",
                    translation: "",
                    tokens: tokens(card["tokens"], language: language),
                    answerTokens: tokens(card["answer_tokens"], language: language),
                    explanation: card.localized("explanation", language: language),
                    reverse: false
                )
            )

        case "reverse_builder":
            return .builder(
                LessonBuilderCard(
                    materialRef: ref,
                    prompt: "",
                    hanzi: card.string("zh"),
                    pinyin: card.string("pinyin"),
                    translation: card.localized("translation", language: language),
                    tokens: tokens(card["tokens"], language: language),
                    answerTokens: tokens(card["answer_tokens"], language: language),
                    explanation: card.localized("explanation", language: language),
                    reverse: true
                )
            )

        default:
            return .unsupported(materialRef: ref, rawType: type)
        }
    }

    private static func choiceCard(
        _ card: [String: JSONValue],
        kind: LessonChoiceKind,
        language: String,
        ref: String
    ) -> LessonCard {
        let lines = card.array("lines").compactMap {
            raw -> LessonDialogLine? in
            guard let line = raw.objectValue else { return nil }
            return LessonDialogLine(
                speaker: line.string("speaker"),
                text: line.string("zh"),
                isBlank: line.bool("blank") ?? false
            )
        }

        return .choice(
            LessonChoiceCard(
                materialRef: ref,
                kind: kind,
                title: card.localized("title", language: language),
                prompt: card.localized("prompt", language: language),
                options: localizedOptions(card["options"], language: language),
                correctIndex: card.int("correct_index") ?? -1,
                explanation: card.localized("explanation", language: language),
                sentence: card.string("sentence"),
                audioText: card.string("audio_text"),
                audioPinyin: kind == .listening ? card.string("pinyin") : "",
                lines: lines,
                reviewOrigin: card.string("review_origin")
            )
        )
    }

    private static func choiceKind(_ type: String) -> LessonChoiceKind? {
        switch type {
        case "meaning_guess": return .meaning
        case "translation_choice": return .translation
        case "hanzi_choice": return .hanzi
        case "pinyin_choice": return .pinyin
        case "quick_quiz": return .quickQuiz
        case "gap_fill": return .gapFill
        case "listening_choice": return .listening
        case "dialog_cloze": return .dialogCloze
        default: return nil
        }
    }

    private static func localizedOptions(
        _ value: JSONValue?,
        language: String
    ) -> [String] {
        value?.arrayValue?.map { $0.localized(language: language) } ?? []
    }

    private static func tokens(
        _ value: JSONValue?,
        language: String
    ) -> [String] {
        if let array = value?.arrayValue {
            return array.compactMap(\.stringValue)
        }
        guard let object = value?.objectValue else { return [] }

        let code: String
        switch language.lowercased() {
        case "uz": code = "uz"
        case "tg", "tj": code = "tj"
        default: code = "ru"
        }

        for key in [code, "ru", "uz", "tj"] {
            if let array = object[key]?.arrayValue {
                return array.compactMap(\.stringValue)
            }
        }
        return []
    }
}
