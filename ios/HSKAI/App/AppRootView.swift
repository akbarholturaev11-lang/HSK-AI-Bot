import SwiftUI

struct AppRootView: View {
    let environment: AppEnvironment

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "character.book.closed.fill")
                    .font(.system(size: 44, weight: .semibold))
                    .accessibilityHidden(true)

                Text("HSK AI")
                    .font(.largeTitle.bold())

                ProgressView()
                    .controlSize(.regular)
            }
            .padding(24)
            .navigationBarHidden(true)
        }
        .tint(.primary)
    }
}

#Preview {
    AppRootView(environment: .production)
}
