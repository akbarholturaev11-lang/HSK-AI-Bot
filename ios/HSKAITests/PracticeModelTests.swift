import XCTest
@testable import HSKAI

final class PracticeModelTests: XCTestCase {
    func testPracticeSessionDecodesServerShape() throws {
        let json = """
        {
          "ok": true,
          "session": {
            "id": "session-123",
            "mode": "placement",
            "skill": "",
            "level": "hsk3",
            "questions": [{
              "id": "q1",
              "level": "hsk3",
              "lesson": 12,
              "type": "choice",
              "subtype": "hanzi_to_meaning",
              "prompt": "选择正确的意思",
              "sentence": "你好",
              "audio_text": "",
              "pinyin": "nǐ hǎo",
              "options": ["Привет", "Спасибо"],
              "answer_index": 0,
              "explanation": "你好 = Привет"
            }]
          }
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(
            IOSPracticeStartResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertTrue(response.ok)
        XCTAssertEqual(response.session?.id, "session-123")
        XCTAssertEqual(response.session?.questions.count, 1)
        XCTAssertEqual(response.session?.questions.first?.answerIndex, 0)
        XCTAssertEqual(response.session?.questions.first?.pinyin, "nǐ hǎo")
    }

    func testPracticeResultDecodesWrongItems() throws {
        let json = """
        {
          "ok": true,
          "score": 8,
          "total": 10,
          "percent": 80,
          "recommendation": "HSK3",
          "wrong_items": [{
            "question": "谢谢",
            "selected_answer": "Привет",
            "correct_answer": "Спасибо",
            "explanation": "谢谢 = Спасибо",
            "pinyin": "xièxie"
          }]
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let result = try decoder.decode(
            IOSPracticeCompleteResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertEqual(result.percent, 80)
        XCTAssertEqual(result.wrongItems.count, 1)
        XCTAssertEqual(result.wrongItems.first?.correctAnswer, "Спасибо")
    }
}
