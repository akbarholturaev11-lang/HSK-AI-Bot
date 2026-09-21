import Foundation
struct IOSAdAPI:Sendable{
 let client:APIClient;let authSession:AuthSession
 func load(placement:String)async throws->IOSAdList{let t=try await authSession.bearerToken();return try await client.get("/api/v3/ios/ad",bearerToken:t,queryItems:[URLQueryItem(name:"slot",value:placement)])}
 func record(_ ad:IOSAd,seconds:Int,lessonOrder:Int=0)async throws->IOSAdViewResponse{let t=try await authSession.bearerToken();return try await client.post("/api/v3/ios/ad/view",body:IOSAdViewRequest(adId:ad.id,watchedSeconds:seconds,lessonOrder:lessonOrder,placement:ad.placement),bearerToken:t)}
}
