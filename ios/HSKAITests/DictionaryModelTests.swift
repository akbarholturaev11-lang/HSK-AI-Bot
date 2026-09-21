import XCTest
@testable import HSKAI

final class DictionaryModelTests: XCTestCase {
    func testDictionaryDecodesCompactSharedShape() throws {
        let json = """
        {
          "ok": true,
          "version": "abc123",
          "language": "uz",
          "words": [
            {"h": "你", "p": "nǐ", "m": "sen", "lv": "1"},
            {"h": "谢谢", "p": "xièxie", "m": "rahmat", "lv": "2"}
          ]
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let payload = try decoder.decode(
            IOSDictionaryResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertTrue(payload.ok)
        XCTAssertEqual(payload.version, "abc123")
        XCTAssertEqual(payload.words.count, 2)
        XCTAssertEqual(payload.words.first?.hanzi, "你")
        XCTAssertEqual(payload.words.first?.pinyin, "nǐ")
        XCTAssertEqual(payload.words.first?.meaning, "sen")
        XCTAssertEqual(payload.words.first?.level, "1")
    }
}
