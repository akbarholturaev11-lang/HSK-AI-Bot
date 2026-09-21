import WidgetKit
import SwiftUI

struct HSKAIEntry: TimelineEntry { let date: Date }
struct HSKAIProvider: TimelineProvider {
    func placeholder(in context: Context) -> HSKAIEntry { .init(date: .now) }
    func getSnapshot(in context: Context, completion: @escaping (HSKAIEntry)->Void) { completion(.init(date:.now)) }
    func getTimeline(in context: Context, completion: @escaping (Timeline<HSKAIEntry>)->Void) {
        let now=Date(); completion(Timeline(entries:[.init(date:now)],policy:.after(now.addingTimeInterval(3600))))
    }
}
struct HSKAIWidgetView: View {
    let entry: HSKAIEntry
    var body: some View {
        VStack(alignment:.leading,spacing:8) {
            HStack { Image(systemName:"character.book.closed.fill"); Text("HSK AI").font(.headline); Spacer() }
            Text(prompt).font(.subheadline.weight(.semibold)).lineLimit(2)
            Text("widget_open").font(.caption)
        }
        .containerBackground(.thinMaterial, for:.widget)
        .widgetURL(URL(string:"pomp-hsk-ai://course"))
    }
    private var prompt:String {
        let h=Calendar.current.component(.hour,from:entry.date)
        if h>=22 || h<6 { return String(localized:"widget_sleep") }
        if h>=19 { return String(localized:"widget_evening") }
        return String(localized:"widget_day")
    }
}
@main struct HSKAIWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind:"HSKAIWidget",provider:HSKAIProvider()){HSKAIWidgetView(entry:$0)}
            .configurationDisplayName("HSK AI")
            .description("widget_description")
            .supportedFamilies([.systemSmall,.systemMedium])
    }
}
