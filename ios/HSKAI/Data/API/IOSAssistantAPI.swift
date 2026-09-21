import Foundation
struct IOSAssistantAPI:Sendable {
 let client:APIClient;let authSession:AuthSession
 func status()async throws->IOSAssistantEnvelope{let t=try await authSession.bearerToken();return try await client.get("/api/v3/ios/assistant/status",queryItems:[URLQueryItem(name:"channel",value:"ios")],bearerToken:t)}
 func conversations()async throws->IOSAssistantEnvelope{let t=try await authSession.bearerToken();return try await client.get("/api/v3/ios/assistant/conversations",bearerToken:t)}
 func create()async throws->IOSAssistantEnvelope{let t=try await authSession.bearerToken();return try await client.post("/api/v3/ios/assistant/conversations",body:EmptyAssistantBody(),bearerToken:t)}
 func history(_ id:String)async throws->IOSAssistantEnvelope{let t=try await authSession.bearerToken();return try await client.get("/api/v3/ios/assistant/conversations/\(id)/messages",bearerToken:t)}
 func send(_ id:String,input:IOSAssistantInput)async throws->IOSAssistantTurn{let t=try await authSession.bearerToken();return try await client.post("/api/v3/ios/assistant/conversations/\(id)/messages",body:input,bearerToken:t)}
 func lookup(_ id:String)async throws->IOSAssistantTurn{let t=try await authSession.bearerToken();return try await client.get("/api/v3/ios/assistant/requests/\(id)",bearerToken:t)}
}
private struct EmptyAssistantBody:Encodable{}
