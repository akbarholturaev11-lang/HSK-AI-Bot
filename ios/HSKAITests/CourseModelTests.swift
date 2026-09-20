import XCTest
@testable import HSKAI

final class CourseModelTests: XCTestCase {
    func testCourseMapDecodesServerShape() throws {
        let json = """
        {
          "ok": true,
          "level": "hsk3",
          "units": [{
            "no": 1,
            "title": {"uz":"Salom","ru":"Привет","tj":"Салом"},
            "status": "current",
            "milestone": null,
            "lessons": [{
              "n": 1,
              "src": 1,
              "part": 1,
              "part_count": 2,
              "checkpoint": false,
              "status": "current",
              "zh": "你好",
              "py": "nǐ hǎo",
              "tr": {"uz":"Salom","ru":"Привет","tj":"Салом"},
              "completion_allowed": true,
              "preview_half": false,
              "locked_premium": false,
              "ad_unlockable": false
            }]
          }],
          "progress": {
            "completed": 0,
            "xp": 45,
            "daily_xp": 20,
            "weekly_xp": 70,
            "streak": 3,
            "longest_streak": 5,
            "league": "Bronze",
            "reward_chest": {"ready":false,"progress":40,"next_xp":50}
          },
          "user": {
            "name": "Akbar",
            "language": "uz",
            "is_paid": false
          },
          "today": {
            "goal_xp": 40,
            "done_xp": 20,
            "streak": 3,
            "total": 2,
            "done": 1,
            "complete": false,
            "tasks": [{
              "type": "continue_lesson",
              "ref": "part:1",
              "skill": null,
              "role": null,
              "done": false,
              "access": "open",
              "available": true
            }]
          }
        }
        """

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let map = try decoder.decode(IOSCourseMap.self, from: Data(json.utf8))

        XCTAssertTrue(map.ok)
        XCTAssertEqual(map.level, "hsk3")
        XCTAssertEqual(map.units.first?.number, 1)
        XCTAssertEqual(map.units.first?.lessons.first?.order, 1)
        XCTAssertEqual(map.units.first?.lessons.first?.partCount, 2)
        XCTAssertEqual(map.progress.xp, 45)
        XCTAssertEqual(map.today?.goalXp, 40)
        XCTAssertEqual(map.units.first?.title.value(language: "tj"), "Салом")
    }
}
