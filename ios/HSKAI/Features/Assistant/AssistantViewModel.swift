import Foundation
@MainActor final class AssistantViewModel:ObservableObject {
 @Published private(set)var enabled=false;@Published private(set)var turns:[IOSAssistantTurn]=[];@Published private(set)var busy=false;@Published private(set)var errorKey:String?
 private let api:IOSAssistantAPI;private var conversationId=""
 init(api:IOSAssistantAPI){self.api=api}
 func open()async{do{let s=try await api.status();enabled=s.enabled ?? false;guard enabled else{return};let cs=try await api.conversations();if let first=cs.conversations.first{conversationId=first.id;turns=(try await api.history(first.id)).messages}}catch{errorKey="assistant_unavailable"}}
 func send(_ text:String,context:IOSAssistantContext = .general)async{let clean=text.trimmingCharacters(in:.whitespacesAndNewlines);guard enabled,!clean.isEmpty,!busy else{return};busy=true;errorKey=nil;do{if conversationId.isEmpty{conversationId=try await api.create().conversation?.id ?? ""};guard !conversationId.isEmpty else{throw AssistantLocalError.noConversation};let id=UUID().uuidString.lowercased();let input=IOSAssistantInput(clientMessageId:id,text:clean,kind:"text",mediaDataUrl:"",context:context);var turn=try await api.send(conversationId,input:input);turns.removeAll{$0.clientMessageId==turn.clientMessageId};turns.append(turn);var attempts=0;while turn.status=="processing" && attempts<35{try await Task.sleep(for:.seconds(attempts<5 ? 2:4));turn=try await api.lookup(id);turns.removeAll{$0.clientMessageId==id};turns.append(turn);attempts+=1}}catch{errorKey="assistant_unavailable"};busy=false}
 func reset(){enabled=false;turns=[];busy=false;errorKey=nil;conversationId=""}
}
private enum AssistantLocalError:Error{case noConversation}
