import XCTest
@testable import HSKAI

final class WordDrillBuilderTests: XCTestCase {
    func testAdaptiveTargetsKeepServerOrderAndReviewFlag() {
        let pool = [
            word("你", "nǐ", "sen"), word("好", "hǎo", "yaxshi"),
            word("我", "wǒ", "men"), word("他", "tā", "u"),
            word("大", "dà", "katta"), word("小", "xiǎo", "kichik"),
            word("来", "lái", "kelmoq"), word("去", "qù", "bormoq")
        ]
        let targets = [
            IOSDrillWord(hanzi: "好", kind: "review", box: 2),
            IOSDrillWord(hanzi: "你", kind: "new", box: 0)
        ]

        let questions = IOSWordDrillBuilder.build(
            targets: targets,
            pool: pool,
            limit: 2
        )

        XCTAssertEqual(questions.map(\.hanzi), ["好", "你"])
        XCTAssertTrue(questions[0].isReview)
        XCTAssertFalse(questions[1].isReview)
        XCTAssertTrue(questions[0].options.contains("好"))
        XCTAssertEqual(questions[0].options.count, 4)
    }

    func testPoolExcludesMultiCharacterWords() {
        let words = [
            word("你", "nǐ", "sen"),
            word("谢谢", "xièxie", "rahmat")
        ]
        XCTAssertEqual(IOSWordDrillBuilder.pool(words).map(\.hanzi), ["你"])
    }

    private func word(_ hanzi: String, _ pinyin: String, _ meaning: String) -> IOSDictionaryWord {
        IOSDictionaryWord(hanzi: hanzi, pinyin: pinyin, meaning: meaning, level: "1")
    }
}
