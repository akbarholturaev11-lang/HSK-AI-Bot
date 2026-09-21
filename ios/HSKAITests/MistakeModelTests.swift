import XCTest
@testable import HSKAI

final class MistakeModelTests: XCTestCase {
    func testOverviewDecodesServerShape() throws {
        let json = """
        {
          "ok": true,
          "summary": {
            "total": 2,
            "categories": {"grammar": 1, "vocabulary": 1}
          },
          "items": [{
            "id": 7,
            "category": "grammar",
            "source": "lesson",
            "level": "hsk3",
            "lesson": 12,
            "question": "我___北京。",
            "sentence": "我住在北京。",
            "audio_text": "",
            "pinyin": "wǒ zhù zài běijīng",
            "user_answer": "有",
            "correct_answer": "住在",
            "explanation": "住在 + place",
            "count": 2
          }]
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(
            IOSMistakesOverviewResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertTrue(response.ok)
        XCTAssertEqual(response.summary.total, 2)
        XCTAssertEqual(response.summary.categories["grammar"], 1)
        XCTAssertEqual(response.items.first?.count, 2)
        XCTAssertEqual(response.items.first?.correctAnswer, "住在")
    }

    func testReviewFeedbackDecodesServerGrading() throws {
        let json = """
        {
          "ok": true,
          "question_id": "q-1",
          "selected_index": 1,
          "correct": false,
          "correct_index": 0,
          "correct_answer": "你好",
          "explanation": "你好 = Salom"
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(
            IOSMistakeReviewAnswerResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertFalse(response.correct)
        XCTAssertEqual(response.correctIndex, 0)
        XCTAssertEqual(response.correctAnswer, "你好")
    }
}
