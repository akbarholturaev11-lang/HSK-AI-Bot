import SwiftUI
struct AdOverlay:View{
 @ObservedObject var model:AdViewModel;let onClose:()->Void
 var body:some View{ZStack{Color.black.opacity(0.56).ignoresSafeArea()
  if model.loading{ProgressView().tint(.white)}
  else if let ad=model.ad{HSKGlassCard(cornerRadius:28,padding:18,tint:HSKColors.auroraBlue){VStack(spacing:14){
   HStack{Text("ad_title").font(.caption.bold()).foregroundStyle(HSKColors.inkSecondary);Spacer();Text(model.canClose ? NSLocalizedString("ad_ready",comment:"") : String(format:NSLocalizedString("ad_wait",comment:""),max(0,model.required-model.elapsed))).font(.caption.bold()).foregroundStyle(HSKColors.cinnabarDark)}
   if let url=URL(string:ad.mediaUrl),ad.mediaType=="photo"{AsyncImage(url:url){$0.resizable().scaledToFit()}placeholder:{ProgressView()}.frame(maxHeight:260).clipShape(RoundedRectangle(cornerRadius:18))}
   if !ad.title.isEmpty{Text(ad.title).font(.headline).foregroundStyle(HSKColors.ink)}
   ProgressView(value:Double(model.elapsed),total:Double(model.required)).tint(HSKColors.cinnabar)
   if let link=ad.linkUrl,let url=URL(string:link){Link(ad.buttonText ?? NSLocalizedString("ad_more",comment:""),destination:url).buttonStyle(HSKGlassSecondaryButtonStyle())}
   Button("ad_continue"){Task{await model.finish();onClose()}}.buttonStyle(HSKPrimaryButtonStyle()).disabled(!model.canClose)
  }}.padding(20)}
 }.onChange(of:model.unavailable){_,v in if v{onClose()}}}
}
