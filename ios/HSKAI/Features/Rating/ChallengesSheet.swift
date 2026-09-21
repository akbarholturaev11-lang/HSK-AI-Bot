import SwiftUI
struct ChallengesSheet: View {
 @ObservedObject var model:ChallengeViewModel
 let account:LinkedAccount
 let onClose:()->Void
 var body: some View { NavigationStack { ZStack { HSKGlassBackdrop(); content }.navigationTitle("challenge_title").toolbar{ToolbarItem(placement:.topBarTrailing){Button("action_close",action:onClose)}} }.task{if model.list==nil{await model.load()}} }
 @ViewBuilder private var content:some View {
  if let s=model.session, s.questions.indices.contains(model.index) { let q=s.questions[model.index]; VStack(spacing:16){Text("\(model.index+1) / \(s.questions.count)").foregroundStyle(HSKColors.inkSecondary);HSKGlassCard(cornerRadius:26,padding:20,tint:HSKColors.auroraBlue){VStack(spacing:8){Text(q.prompt).font(.headline);if !q.sentence.isEmpty{Text(q.sentence).font(.title3.bold())}}};ForEach(Array(q.options.enumerated()),id:\.offset){i,o in Button(o){Task{await model.answer(i)}}.buttonStyle(HSKGlassSecondaryButtonStyle())};Spacer()}.padding(18)
  } else if let list=model.list { ScrollView{VStack(spacing:12){if list.items.isEmpty{HSKGlassCard(cornerRadius:24,padding:20){Text("challenge_empty").foregroundStyle(HSKColors.inkSecondary)}};ForEach(list.items){c in HSKGlassCard(cornerRadius:22,padding:16,tint:c.status=="pending" ? HSKColors.auroraBlue:nil){VStack(alignment:.leading,spacing:10){Text(c.otherUser.name.isEmpty ? c.otherUser.username:c.otherUser.name).font(.headline);Text(LocalizedStringKey("challenge_status_\(c.status)")).font(.caption).foregroundStyle(HSKColors.inkSecondary);HStack{if c.status=="pending" && c.viewerRole=="opponent"{Button("challenge_accept"){Task{await model.respond(c.id,"accept")}}.buttonStyle(HSKPrimaryButtonStyle());Button("challenge_decline"){Task{await model.respond(c.id,"decline")}}.buttonStyle(HSKGlassSecondaryButtonStyle())}else if c.status=="active" && !c.viewerDone{Button("challenge_start"){Task{await model.start(c.id)}}.buttonStyle(HSKPrimaryButtonStyle())}}}}}}.padding(16)}
  } else { ProgressView().tint(HSKColors.cinnabar) }
 }
}
