import Foundation

enum AppVersion {
    static var current: String {
        let value = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleShortVersionString"
        ) as? String
        return value?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
            ? value!
            : "0.0.0"
    }
}
