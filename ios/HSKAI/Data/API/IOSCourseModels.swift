import Foundation

struct IOSLocalizedText: Codable, Sendable, Equatable {
    let uz: String
    let ru: String
    let tj: String

    func value(language: String) -> String {
        switch language.lowercased() {
        case "uz": return firstNonEmpty(uz, ru, tj)
        case "tg", "tj": return firstNonEmpty(tj, ru, uz)
        default: return firstNonEmpty(ru, uz, tj)
        }
    }

    private func firstNonEmpty(_ values: String...) -> String {
        values.first(where: { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) ?? ""
    }
}

struct IOSCourseMap: Codable, Sendable, Equatable {
    let ok: Bool
    let level: String
    let units: [IOSCourseUnit]
    let progress: IOSCourseProgress
    let user: IOSCourseUser
    let today: IOSCourseToday?
    let foundation: IOSCourseFoundation?
}

struct IOSCourseFoundation: Codable, Sendable, Equatable {
    let id: String
    let version: Int
    let required: Bool
    let completed: Bool
    let status: String
}

struct IOSCourseUnit: Codable, Sendable, Equatable, Identifiable {
    let number: Int
    let title: IOSLocalizedText
    let status: String?
    let milestone: IOSCourseMilestone?
    let lessons: [IOSCourseLesson]
    var id: Int { number }

    enum CodingKeys: String, CodingKey {
        case number = "no", title, status, milestone, lessons
    }
}

struct IOSCourseMilestone: Codable, Sendable, Equatable {
    let title: IOSLocalizedText
    let status: String
}

struct IOSCourseLesson: Codable, Sendable, Equatable, Identifiable {
    let order: Int
    let sourceLesson: Int
    let part: Int
    let partCount: Int
    let checkpoint: Bool
    let status: String
    let hanzi: String
    let pinyin: String
    let subtitle: IOSLocalizedText
    let completionAllowed: Bool
    let previewHalf: Bool?
    let lockedPremium: Bool?
    let adUnlockable: Bool?
    var id: Int { order }

    enum CodingKeys: String, CodingKey {
        case order = "n"
        case sourceLesson = "src"
        case part, partCount, checkpoint, status
        case hanzi = "zh"
        case pinyin = "py"
        case subtitle = "tr"
        case completionAllowed, previewHalf, lockedPremium, adUnlockable
    }
}

struct IOSCourseProgress: Codable, Sendable, Equatable {
    let completed: Int
    let xp: Int
    let dailyXp: Int
    let weeklyXp: Int
    let streak: Int
    let longestStreak: Int
    let league: String
    let rewardChest: IOSRewardChest?
}

struct IOSRewardChest: Codable, Sendable, Equatable {
    let ready: Bool
    let progress: Int
    let nextXp: Int
}

struct IOSCourseUser: Codable, Sendable, Equatable {
    let name: String
    let language: String
    let isPaid: Bool
}

struct IOSCourseToday: Codable, Sendable, Equatable {
    let goalXp: Int
    let doneXp: Int
    let streak: Int
    let total: Int
    let done: Int
    let complete: Bool
    let tasks: [IOSCourseTodayTask]
}

struct IOSCourseTodayTask: Codable, Sendable, Equatable, Identifiable {
    let type: String
    let ref: String?
    let skill: String?
    let role: String?
    let done: Bool
    let access: String
    let available: Bool

    var id: String {
        [type, ref ?? "", skill ?? "", role ?? ""].joined(separator: ":")
    }
}

struct IOSStudyPreferencesRequest: Encodable, Sendable {
    let goal: String?
    let dailyMinutes: Int?
    let dailyGoalXp: Int?
    let preferredFocus: String?
}

struct IOSStudyPreferencesResponse: Decodable, Sendable {
    let ok: Bool
}
