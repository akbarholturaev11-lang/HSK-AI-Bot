import Foundation
struct IOSAdList:Decodable,Sendable{let ok:Bool;let ads:[IOSAd];let slot:String;let channel:String}
struct IOSAd:Decodable,Sendable,Identifiable{let id:Int;let title:String;let mediaType:String;let mediaUrl:String;let linkUrl:String?;let adType:String;let buttonText:String?;let durationSeconds:Int;let placement:String;let skipAfterSeconds:Int}
struct IOSAdViewRequest:Encodable{let adId:Int;let watchedSeconds:Int;let lessonOrder:Int;let placement:String}
struct IOSAdViewResponse:Decodable,Sendable{let ok:Bool;let requiredSeconds:Int?;let watchedSeconds:Int?}
