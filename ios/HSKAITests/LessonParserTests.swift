import XCTest
@testable import HSKAI

final class LessonParserTests: XCTestCase {
    func testMaterialReferenceMatchesServerContract() {
        XCTAssertEqual(
            IOSLessonParser.materialRef(
                level: "hsk1",
                lessonOrder: 2,
                sectionNo: 3,
                cardNo: 4
            ),
            "lesson:hsk1:2:section:3:card:4"
        )
    }

    func testLessonParserHandlesLocalizedChoiceAndBuilder() throws {
        let json = """
        {
          "ok": true,
          "level": "hsk1",
          "lesson_order": 1,
          "completion_allowed": true,
          "lesson": {
            "source_lesson": 1,
            "part_no": 1,
            "part_count": 3,
            "checkpoint": false,
            "title": "你好",
            "subtitle": {"uz":"Salom","ru":"Привет","tj":"Салом"},
            "sections": [{
              "section_no": 1,
              "section_title": {"uz":"Mashq","ru":"Упражнение","tj":"Машқ"},
              "section_purpose": "practice",
              "cards": [
                {
                  "type":"meaning_guess",
                  "title":{"uz":"Ma'no","ru":"Значение","tj":"Маъно"},
                  "prompt":{"uz":"Tanlang","ru":"Выберите","tj":"Интихоб кунед"},
                  "options":[
                    {"uz":"Salom","ru":"Привет","tj":"Салом"},
                    {"uz":"Xayr","ru":"Пока","tj":"Хайр"}
                  ],
                  "correct_index":0,
                  "explanation":{"uz":"To'g'ri","ru":"Верно","tj":"Дуруст"}
                },
                {
                  "type":"sentence_builder",
                  "sentence":{"uz":"Salom","ru":"Привет","tj":"Салом"},
                  "tokens":["好","你"],
                  "answer_tokens":["你","好"],
                  "explanation":{"uz":"你好","ru":"你好","tj":"你好"}
                }
              ]
            }]
          }
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(IOSLessonResponse.self, from: Data(json.utf8))
        let lesson = IOSLessonParser.parse(response: response, language: "uz")

        XCTAssertEqual(lesson.title, "你好")
        XCTAssertEqual(lesson.subtitle, "Salom")
        XCTAssertEqual(lesson.cards.count, 2)

        guard case .choice(let choice) = lesson.cards[0] else {
            return XCTFail("Expected choice card")
        }
        XCTAssertEqual(choice.options, ["Salom", "Xayr"])
        XCTAssertEqual(choice.correctIndex, 0)
        XCTAssertEqual(choice.materialRef, "lesson:hsk1:1:section:1:card:1")

        guard case .builder(let builder) = lesson.cards[1] else {
            return XCTFail("Expected builder card")
        }
        XCTAssertEqual(builder.answerTokens, ["你", "好"])
        XCTAssertEqual(builder.materialRef, "lesson:hsk1:1:section:1:card:2")
    }

    func testFoundationParserCoversRequiredObjectiveCards() throws {
        let json = """
        {
          "id":"starter0_hsk1",
          "version":1,
          "required_objectives":["meaning","build","listen"],
          "cards":[
            {
              "type":"choice",
              "card_id":"starter0_meaning",
              "objective_id":"meaning",
              "title":{"uz":"Ma'no","ru":"Значение","tj":"Маъно"},
              "prompt":{"uz":"Tanlang","ru":"Выберите","tj":"Интихоб кунед"},
              "options":[
                {"uz":"Salom","ru":"Привет","tj":"Салом"},
                {"uz":"Rahmat","ru":"Спасибо","tj":"Раҳмат"}
              ],
              "correct_index":0,
              "explanation":{"uz":"To'g'ri","ru":"Верно","tj":"Дуруст"}
            },
            {
              "type":"builder",
              "card_id":"starter0_build",
              "objective_id":"build",
              "title":{"uz":"Tuzing","ru":"Соберите","tj":"Созед"},
              "prompt":{"uz":"Salom","ru":"Привет","tj":"Салом"},
              "tokens":["好","你"],
              "answer_tokens":["你","好"],
              "explanation":{"uz":"你好","ru":"你好","tj":"你好"}
            }
          ]
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let payload = try decoder.decode(IOSFoundationPayload.self, from: Data(json.utf8))
        let cards = FoundationParser.parse(payload, language: "tj")

        XCTAssertEqual(cards.count, 2)
        guard case .choice(let choice) = cards[0] else {
            return XCTFail("Expected choice")
        }
        XCTAssertEqual(choice.objectiveId, "meaning")
        XCTAssertEqual(choice.options.first, "Салом")

        guard case .builder(let builder) = cards[1] else {
            return XCTFail("Expected builder")
        }
        XCTAssertEqual(builder.answerTokens, ["你", "好"])
    }
}


extension LessonParserTests {
    func testCheckpointExitTicketUsesStableSection99References() throws {
        let json = """
        {
          "ok": true,
          "level": "hsk1",
          "lesson_order": 5,
          "lesson": {
            "title":"复习",
            "sections":[],
            "exit_ticket":{
              "cards":[
                {
                  "type":"choice",
                  "title":{"uz":"Ma'no","ru":"Значение","tj":"Маъно"},
                  "prompt":{"uz":"Tanlang","ru":"Выберите","tj":"Интихоб кунед"},
                  "options":[
                    {"uz":"Salom","ru":"Привет","tj":"Салом"},
                    {"uz":"Xayr","ru":"Пока","tj":"Хайр"}
                  ],
                  "correct_index":0,
                  "explanation":{"uz":"To'g'ri","ru":"Верно","tj":"Дуруст"}
                }
              ]
            }
          }
        }
        """
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(IOSLessonResponse.self, from: Data(json.utf8))
        let lesson = IOSLessonParser.parse(response: response, language: "uz")

        XCTAssertEqual(lesson.sections.last?.sectionNo, 99)
        XCTAssertEqual(
            lesson.cards.last?.materialRef,
            "lesson:hsk1:5:section:99:card:1"
        )
    }
}
