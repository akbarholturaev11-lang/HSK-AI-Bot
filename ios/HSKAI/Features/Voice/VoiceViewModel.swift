import Foundation
@MainActor final class VoiceViewModel:ObservableObject {
 enum Phase:Equatable { case idle,loading,active,ending,finished }
 @Published private(set)var phase:Phase = .idle
 @Published private(set)var status:IOSVoiceStatus?
 @Published private(set)var startPayload:IOSVoiceStartResponse?
 @Published private(set)var turns:[IOSVoiceTurn]=[]
 @Published private(set)var suggestions:[IOSVoiceSuggestion]=[]
 @Published private(set)var isRecording=false
 @Published private(set)var errorKey:String?
 @Published private(set)var summary:IOSVoiceEndResponse?
 private let api:IOSVoiceAPI; private let recorder=MandarinAudioRecorder(); private let speech=MandarinSpeechPlayer()
 init(api:IOSVoiceAPI){self.api=api}
 func loadStatus() async { do{status=try await api.status()}catch{errorKey="voice_load_error"} }
 func start(role:String,account:LinkedAccount) async { phase = .loading; errorKey=nil; do{let r=try await api.start(role:role,level:Self.level(account.level),language:Self.lang(account.language));startPayload=r;suggestions=r.openingMessage.suggestions;turns=[IOSVoiceTurn(user:"",chinese:r.openingMessage.chineseReply,pinyin:r.openingMessage.pinyin,translation:r.openingMessage.translation,correction:r.openingMessage.correction)];phase = .active;speech.play(r.openingMessage.chineseReply)}catch{phase = .idle;errorKey="voice_start_error"}}
 func send(text:String) async { guard let id=startPayload?.sessionId,!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return}; await sendTurn(id:id,text:text,audio:"") }
 func speak() async { guard let id=startPayload?.sessionId,!isRecording else{return};guard await recorder.requestPermission() else{errorKey="pronunciation_permission_denied";return};do{try recorder.start();isRecording=true;try await Task.sleep(for:.milliseconds(3200));let data=try recorder.stopDataURL();isRecording=false;await sendTurn(id:id,text:"",audio:data)}catch{recorder.cancel();isRecording=false;errorKey="voice_message_error"}}
 private func sendTurn(id:String,text:String,audio:String) async { errorKey=nil;do{let r=try await api.message(sessionId:id,text:text,audioDataUrl:audio);turns.append(.init(user:r.transcription.isEmpty ? text:r.transcription,chinese:r.chineseReply,pinyin:r.pinyin,translation:r.translation,correction:r.correction));suggestions=r.suggestions;speech.play(r.chineseReply);if r.sessionShouldEnd{await end()}}catch{errorKey="voice_message_error"}}
 func end() async { guard let id=startPayload?.sessionId else{return};phase = .ending;do{summary=try await api.end(sessionId:id);phase = .finished}catch{phase = .active;errorKey="voice_end_error"}}
 func reset(){recorder.cancel();speech.stop();phase = .idle;status=nil;startPayload=nil;turns=[];suggestions=[];isRecording=false;errorKey=nil;summary=nil}
 private static func lang(_ x:String)->String { switch x.lowercased(){case "uz":return "uz";case "tj","tg":return "tj";default:return "ru"}}
 private static func level(_ x:String)->String { let y=x.lowercased();return ["beginner","hsk1","hsk2","hsk3","hsk4"].contains(y) ? y:"hsk1" }
}
