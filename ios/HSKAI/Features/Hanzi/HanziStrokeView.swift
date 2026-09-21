import SwiftUI
struct HanziStrokeView: View {
    let text: String
    @State private var visible = 1
    @State private var playing = false
    private var characters:[Character]{Array(text.filter{String($0).range(of:"[\\p{Han}]",options:.regularExpression) != nil})}
    var body:some View {
        HSKGlassCard(cornerRadius:24,padding:16,tint:HSKColors.auroraBlue){
            VStack(spacing:14){
                HStack{Label("stroke_title",systemImage:"pencil.and.scribble").font(.headline).foregroundStyle(HSKColors.ink);Spacer();Text("\(min(visible,characters.count))/\(characters.count)").font(.caption.monospacedDigit()).foregroundStyle(HSKColors.inkSecondary)}
                if characters.isEmpty { Text("stroke_unavailable").foregroundStyle(HSKColors.inkSecondary) }
                else {
                    HStack(spacing:10){ForEach(Array(characters.enumerated()),id:\.offset){i,ch in
                        ZStack{RoundedRectangle(cornerRadius:14).fill(.ultraThinMaterial).frame(width:62,height:62)
                            Path{p in p.move(to:CGPoint(x:31,y:7));p.addLine(to:CGPoint(x:31,y:55));p.move(to:CGPoint(x:7,y:31));p.addLine(to:CGPoint(x:55,y:31))}.stroke(HSKColors.inkSecondary.opacity(0.18),style:StrokeStyle(lineWidth:0.8,dash:[3,3])).frame(width:62,height:62)
                            Text(String(ch)).font(.system(size:42,weight:.medium)).foregroundStyle(i < visible ? HSKColors.ink : HSKColors.ink.opacity(0.12))
                        }
                    }}
                    HStack{Button("stroke_reset"){playing=false;visible=1}.buttonStyle(HSKGlassSecondaryButtonStyle())
                        Button{play()}label:{Label(playing ? "stroke_playing":"stroke_play",systemImage:playing ? "pause.fill":"play.fill")}.buttonStyle(HSKGlassSecondaryButtonStyle()).disabled(playing)}
                }
            }
        }
    }
    private func play(){guard !characters.isEmpty else{return};playing=true;visible=0;Task{@MainActor in for i in 1...characters.count{if !playing{return};visible=i;try? await Task.sleep(for:.milliseconds(650))};playing=false}}
}
