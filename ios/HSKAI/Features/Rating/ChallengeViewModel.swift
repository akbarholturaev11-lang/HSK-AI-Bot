import Foundation
@MainActor
final class ChallengeViewModel: ObservableObject {
 @Published private(set) var list: IOSChallengeList?
 @Published private(set) var session: IOSChallengeSession?
 @Published private(set) var index=0
 @Published private(set) var answers:[IOSChallengeAnswer]=[]
 @Published private(set) var isLoading=false
 @Published private(set) var errorKey:String?
 private let api:IOSChallengeAPI
 private var startedAt=Date()
 init(api:IOSChallengeAPI){self.api=api}
 func load() async { guard !isLoading else{return};isLoading=true;defer{isLoading=false};do{list=try await api.list()}catch{errorKey="challenge_load_error"}}
 func create(ref:String,account:LinkedAccount) async { guard !ref.isEmpty else{return};isLoading=true;defer{isLoading=false};do{_ = try await api.create(opponentRef:ref,level:account.level,language:account.language);await load()}catch{errorKey="challenge_action_error"}}
 func respond(_ id:Int,_ action:String) async {isLoading=true;defer{isLoading=false};do{_ = try await api.respond(id:id,action:action);await load()}catch{errorKey="challenge_action_error"}}
 func start(_ id:Int) async {isLoading=true;defer{isLoading=false};do{let r=try await api.start(id:id);session=r.session;index=0;answers=[];startedAt=Date()}catch{errorKey="challenge_action_error"}}
 func answer(_ selected:Int) async {guard let s=session,s.questions.indices.contains(index) else{return};answers.append(.init(questionId:s.questions[index].id,selectedIndex:selected));if index+1<s.questions.count{index+=1}else{do{_ = try await api.submit(id:s.challengeId,answers:answers,duration:max(0,Int(Date().timeIntervalSince(startedAt))));session=nil;await load()}catch{errorKey="challenge_action_error"}}}
 func reset(){list=nil;session=nil;index=0;answers=[];errorKey=nil}
}
