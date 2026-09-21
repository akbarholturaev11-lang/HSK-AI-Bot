import Foundation
@MainActor final class AdViewModel:ObservableObject{
 @Published var ad:IOSAd?;@Published var elapsed=0;@Published var loading=false;@Published var unavailable=false
 let api:IOSAdAPI;private var ticker:Task<Void,Never>?
 init(api:IOSAdAPI){self.api=api}
 var required:Int{max(1,ad?.skipAfterSeconds ?? ad?.durationSeconds ?? 1)}
 var canClose:Bool{elapsed>=required}
 func load(placement:String)async{ticker?.cancel();loading=true;unavailable=false;elapsed=0;do{ad=try await api.load(placement:placement).ads.first;unavailable=ad==nil}catch{unavailable=true};loading=false;if ad != nil{ticker=Task{[weak self] in while let self,!Task.isCancelled,!self.canClose{try? await Task.sleep(for:.seconds(1));if !Task.isCancelled{self.elapsed+=1}}}}}
 func finish()async{guard let ad,canClose else{return};_ = try? await api.record(ad,seconds:elapsed);ticker?.cancel()}
 func reset(){ticker?.cancel();ad=nil;elapsed=0;unavailable=false}
}
