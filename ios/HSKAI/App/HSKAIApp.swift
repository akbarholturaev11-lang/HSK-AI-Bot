import SwiftUI

@main
struct HSKAIApp: App {
    private let environment = AppEnvironment.production

    var body: some Scene {
        WindowGroup {
            AppRootView(environment: environment)
        }
    }
}
