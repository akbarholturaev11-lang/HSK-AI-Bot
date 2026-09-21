import Foundation
struct IOSChallengeAPI: Sendable {
    let client: APIClient
    let authSession: AuthSession
    func list() async throws -> IOSChallengeList { let t=try await authSession.bearerToken(); return try await client.get("/api/v3/ios/challenges",bearerToken:t) }
    func create(opponentRef:String,level:String,language:String) async throws -> IOSChallengeAction { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/challenges",body:IOSChallengeCreate(opponentRef:opponentRef,level:level,language:language),bearerToken:t) }
    func respond(id:Int,action:String) async throws -> IOSChallengeAction { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/challenges/\(id)/respond",body:IOSChallengeRespond(action:action),bearerToken:t) }
    func start(id:Int) async throws -> IOSChallengeStart { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/challenges/\(id)/start",body:EmptyChallengeBody(),bearerToken:t) }
    func submit(id:Int,answers:[IOSChallengeAnswer],duration:Int) async throws -> IOSChallengeAction { let t=try await authSession.bearerToken(); return try await client.post("/api/v3/ios/challenges/\(id)/submit",body:IOSChallengeSubmit(answers:answers,durationSeconds:duration),bearerToken:t) }
}
private struct EmptyChallengeBody: Encodable {}
