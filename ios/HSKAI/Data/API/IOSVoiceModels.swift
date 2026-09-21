import Foundation

struct IOSVoiceStatus: Decodable, Sendable {
    let ok: Bool
    let isPaid: Bool
    let plan: String
    let remainingVoiceLimit: Int
    let level: String
    let language: String
    let completedLessons: Int
    let resetAt: String?
}
struct IOSVoiceStartRequest: Encodable { let role:String; let level:String; let language:String; let voice:String }
struct IOSVoiceStartResponse: Decodable, Sendable {
    let ok:Bool; let sessionId:String; let remainingLimit:Int; let character:String
    let openingMessage:IOSVoiceReply; let maxDialogs:Int; let courseContext:IOSVoiceCourseContext
}
struct IOSVoiceCourseContext: Decodable, Sendable { let title:String; let words:[IOSVoiceWord]; let reviewWords:[IOSVoiceWord] }
struct IOSVoiceWord: Decodable, Sendable, Identifiable {
    var id:String { "\(hanzi)-\(pinyin)" }
    let hanzi:String; let pinyin:String; let meaning:String
    enum CodingKeys:String,CodingKey { case hanzi="zh",pinyin,meaning }
}
struct IOSVoiceSuggestion: Decodable, Sendable, Identifiable {
    var id:String { "\(hanzi)-\(pinyin)-\(translation)" }
    let hanzi:String; let pinyin:String; let translation:String
    enum CodingKeys:String,CodingKey { case hanzi="zh",pinyin,translation }
}
struct IOSVoiceReply: Decodable, Sendable {
    let chineseReply:String; let pinyin:String; let translation:String; let correction:String?; let suggestions:[IOSVoiceSuggestion]
}
struct IOSVoiceMessageRequest: Encodable { let sessionId:String; let audioDataUrl:String; let text:String }
struct IOSVoiceMessageResponse: Decodable, Sendable {
    let ok:Bool; let transcription:String; let chineseReply:String; let pinyin:String; let translation:String
    let correction:String?; let remainingLimit:Int; let turnCount:Int; let maxDialogs:Int; let sessionShouldEnd:Bool
    let suggestions:[IOSVoiceSuggestion]
}
struct IOSVoiceEndRequest: Encodable { let sessionId:String }
struct IOSVoiceTranscript: Decodable, Sendable, Identifiable {
    var id:String { "\(user)-\(assistant)-\(pinyin)" }
    let user:String; let assistant:String; let pinyin:String; let translation:String; let correction:String?; let good:Bool
}
struct IOSVoiceEndResponse: Decodable, Sendable {
    let ok:Bool; let durationSeconds:Int; let messageCount:Int; let goodCount:Int; let mistakeCount:Int; let transcript:[IOSVoiceTranscript]
}
struct IOSVoiceTurn: Identifiable, Sendable {
    let id=UUID(); let user:String; let chinese:String; let pinyin:String; let translation:String; let correction:String?
}
