import Foundation
struct IOSVoiceAPI: Sendable {
 let client:APIClient; let authSession:AuthSession
 func status() async throws -> IOSVoiceStatus { let t=try await authSession.bearerToken(); return try await client.get("/api/v3/ios/voice/status",bearerToken:t) }
 func start(role:String,level:String,language:String,voice:String="female") async throws -> IOSVoiceStartResponse { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/voice/session/start",body:IOSVoiceStartRequest(role:role,level:level,language:language,voice:voice),bearerToken:t) }
 func message(sessionId:String,text:String="",audioDataUrl:String="") async throws -> IOSVoiceMessageResponse { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/voice/message",body:IOSVoiceMessageRequest(sessionId:sessionId,audioDataUrl:audioDataUrl,text:text),bearerToken:t) }
 func end(sessionId:String) async throws -> IOSVoiceEndResponse { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/voice/session/end",body:IOSVoiceEndRequest(sessionId:sessionId),bearerToken:t) }
}
