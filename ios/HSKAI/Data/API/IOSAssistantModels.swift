import Foundation
struct IOSAssistantContext:Codable,Sendable {
 let screen:String;let title:String;let details:String;let materialRef:String;let attemptId:String;let revision:String;let answerState:String
 static let general=Self(screen:"general",title:"",details:"",materialRef:"",attemptId:"",revision:"",answerState:"")
}
struct IOSAssistantInput:Encodable,Sendable { let clientMessageId:String;let text:String;let kind:String;let mediaDataUrl:String;let context:IOSAssistantContext }
struct IOSAssistantAction:Decodable,Sendable,Identifiable { var id:String{"\(label)-\(destination)"};let label:String;let destination:String }
struct IOSAssistantSource:Decodable,Sendable,Identifiable { var id:String{"\(label)-\(materialRef)"};let label:String;let materialRef:String }
struct IOSAssistantConversation:Decodable,Sendable,Identifiable { let id:String;let title:String }
struct IOSAssistantTurn:Decodable,Sendable,Identifiable {
 var id:String{clientMessageId}
 let clientMessageId:String;let conversationId:String;let userText:String;let kind:String;let status:String;let phase:String;let error:String;let context:IOSAssistantContext;let text:String;let transcript:String;let actions:[IOSAssistantAction];let sources:[IOSAssistantSource]
}
struct IOSAssistantEnvelope:Decodable,Sendable {
 let ok:Bool;let enabled:Bool?;let error:String;let conversation:IOSAssistantConversation?;let conversations:[IOSAssistantConversation];let messages:[IOSAssistantTurn];let nextCursor:String;let assessmentActive:Bool?
 enum CodingKeys:String,CodingKey{case ok,enabled,error,conversation,conversations,messages,nextCursor,assessmentActive}
 init(from decoder:Decoder)throws{
  let c=try decoder.container(keyedBy:CodingKeys.self)
  ok=try c.decodeIfPresent(Bool.self,forKey:.ok) ?? false
  enabled=try c.decodeIfPresent(Bool.self,forKey:.enabled)
  error=try c.decodeIfPresent(String.self,forKey:.error) ?? ""
  conversation=try c.decodeIfPresent(IOSAssistantConversation.self,forKey:.conversation)
  conversations=try c.decodeIfPresent([IOSAssistantConversation].self,forKey:.conversations) ?? []
  messages=try c.decodeIfPresent([IOSAssistantTurn].self,forKey:.messages) ?? []
  nextCursor=try c.decodeIfPresent(String.self,forKey:.nextCursor) ?? ""
  assessmentActive=try c.decodeIfPresent(Bool.self,forKey:.assessmentActive)
 }
}
