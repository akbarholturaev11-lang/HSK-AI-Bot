import XCTest
@testable import HSKAI

final class ExamModelTests: XCTestCase {
    func testExamSessionDecodesServerShape() throws {
        let json = """
        {
          "ok": true,
          "session": {
            "id": "exam-session-123",
            "level": "hsk3",
            "duration_min": 35,
            "pass_score": 60,
            "questions": [{
              "id": "q1",
              "format": "choice",
              "section": "listening",
              "prompt": "Eshiting",
              "sentence": "",
              "audio_text": "你好",
              "options": ["Salom", "Rahmat"]
            }]
          }
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(
            IOSExamStartResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertTrue(response.ok)
        XCTAssertEqual(response.session?.durationMin, 35)
        XCTAssertEqual(response.session?.passScore, 60)
        XCTAssertEqual(response.session?.questions.first?.section, "listening")
        XCTAssertEqual(response.session?.questions.first?.audioText, "你好")
    }

    func testExamResultDecodesSectionScores() throws {
        let json = """
        {
          "ok": true,
          "duplicate": false,
          "score": 10,
          "total": 12,
          "percent": 83,
          "pass_score": 60,
          "passed": true,
          "section_scores": {
            "listening": {"score": 4, "total": 5, "percent": 80},
            "reading": {"score": 4, "total": 4, "percent": 100},
            "writing": {"score": 2, "total": 3, "percent": 67}
          },
          "wrong_items": []
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let result = try decoder.decode(
            IOSExamCompleteResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertTrue(result.passed)
        XCTAssertEqual(result.percent, 83)
        XCTAssertEqual(result.sectionScores["writing"]?.score, 2)
        XCTAssertEqual(result.sectionScores["listening"]?.total, 5)
    }

    func testCurrentLevelCanBePromotedToTopOfCenter() {
        let api = IOSExamEntry.all
        XCTAssertEqual(api.map(\.level), ["hsk1", "hsk2", "hsk3", "hsk4"])
    }
}
