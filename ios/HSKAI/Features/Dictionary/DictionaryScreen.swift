import SwiftUI

struct DictionaryScreen: View {
    @ObservedObject var model: DictionaryViewModel
    @State private var selectedWord: IOSDictionaryWord?

    var body: some View {
        NavigationStack {
            ZStack {
                HSKGlassBackdrop()
                content
            }
            .navigationTitle("tab_dictionary")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $model.query, prompt: "dictionary_search")
            .task { await model.load() }
            .sheet(item: $selectedWord) { word in
                wordSheet(word)
                    .presentationDetents([.medium])
                    .presentationDragIndicator(.visible)
                    .presentationBackground(.ultraThinMaterial)
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        if model.isLoading && model.response == nil {
            ProgressView().tint(HSKColors.cinnabar).controlSize(.large)
        } else if let response = model.response {
            ScrollView(showsIndicators: false) {
                VStack(spacing: 12) {
                    HSKGlassCard(cornerRadius: 24, padding: 16, tint: HSKColors.auroraBlue) {
                        VStack(spacing: 12) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("dictionary_all_words")
                                        .font(.headline)
                                        .foregroundStyle(HSKColors.ink)
                                    Text("\(model.filteredWords.count) / \(response.words.count)")
                                        .font(.caption.monospacedDigit())
                                        .foregroundStyle(HSKColors.inkSecondary)
                                }
                                Spacer()
                                Image(systemName: "character.book.closed.fill")
                                    .font(.title2)
                                    .foregroundStyle(HSKColors.cinnabarDark)
                            }

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    filter("all", title: "dictionary_filter_all")
                                    ForEach(1...4, id: \.self) { level in
                                        filter("hsk\(level)", title: "HSK \(level)")
                                    }
                                }
                            }
                        }
                    }

                    if model.filteredWords.isEmpty {
                        HSKGlassCard(cornerRadius: 22, padding: 18) {
                            Text("dictionary_empty")
                                .foregroundStyle(HSKColors.inkSecondary)
                                .frame(maxWidth: .infinity)
                        }
                    } else {
                        LazyVStack(spacing: 9) {
                            ForEach(model.filteredWords) { word in
                                Button { selectedWord = word } label: {
                                    HSKGlassCard(cornerRadius: 20, padding: 14) {
                                        HStack(spacing: 14) {
                                            Text(word.hanzi)
                                                .font(.system(size: 30, weight: .semibold, design: .rounded))
                                                .foregroundStyle(HSKColors.ink)
                                                .frame(minWidth: 54)

                                            VStack(alignment: .leading, spacing: 3) {
                                                Text(word.pinyin)
                                                    .font(.subheadline.weight(.semibold))
                                                    .foregroundStyle(HSKColors.cinnabarDark)
                                                Text(word.meaning)
                                                    .font(.subheadline)
                                                    .foregroundStyle(HSKColors.inkSecondary)
                                                    .lineLimit(2)
                                            }

                                            Spacer()

                                            Text(levelLabel(word.level))
                                                .font(.caption2.bold())
                                                .foregroundStyle(HSKColors.inkSecondary)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 5)
                                                .background(.ultraThinMaterial, in: Capsule())
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        } else {
            HSKGlassCard(cornerRadius: 26, padding: 20, tint: HSKColors.flame) {
                VStack(spacing: 14) {
                    Text(LocalizedStringKey(model.errorKey ?? "dictionary_load_error"))
                        .foregroundStyle(HSKColors.inkSecondary)
                    Button("action_retry") {
                        Task { await model.load(force: true) }
                    }
                    .buttonStyle(HSKGlassSecondaryButtonStyle())
                }
            }
            .padding(24)
        }
    }

    private func filter(_ value: String, title: String) -> some View {
        Button {
            model.levelFilter = value
        } label: {
            Text(LocalizedStringKey(title))
                .font(.caption.weight(.bold))
                .foregroundStyle(model.levelFilter == value ? HSKColors.cinnabarDark : HSKColors.inkSecondary)
                .padding(.horizontal, 13)
                .padding(.vertical, 8)
                .background(
                    model.levelFilter == value
                        ? HSKColors.cinnabar.opacity(0.12)
                        : Color.white.opacity(0.10),
                    in: Capsule()
                )
                .overlay(
                    Capsule().stroke(
                        model.levelFilter == value
                            ? HSKColors.cinnabar.opacity(0.45)
                            : Color.white.opacity(0.35),
                        lineWidth: 0.8
                    )
                )
        }
        .buttonStyle(.plain)
    }

    private func wordSheet(_ word: IOSDictionaryWord) -> some View {
        ZStack {
            HSKGlassBackdrop()
            VStack(spacing: 12) {
                Text(word.hanzi)
                    .font(.system(size: 64, weight: .semibold, design: .rounded))
                    .foregroundStyle(HSKColors.ink)
                Text(word.pinyin)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(HSKColors.cinnabarDark)
                Text(word.meaning)
                    .font(.title3)
                    .foregroundStyle(HSKColors.inkSecondary)
                    .multilineTextAlignment(.center)
                HSKGlassPill {
                    Text(levelLabel(word.level))
                        .font(.caption.bold())
                        .foregroundStyle(HSKColors.ink)
                }
            }
            .padding(30)
        }
    }

    private func levelLabel(_ value: String) -> String {
        let digits = value.filter(\.isNumber)
        if let first = digits.first { return "HSK \(first)" }
        return value.uppercased()
    }
}
