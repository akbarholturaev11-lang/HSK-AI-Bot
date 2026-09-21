import Foundation
import UserNotifications

@MainActor
final class StudyReminderManager: ObservableObject {
    @Published private(set) var enabled = UserDefaults.standard.bool(forKey: "studyReminderEnabled")
    @Published private(set) var permissionDenied = false

    private let center = UNUserNotificationCenter.current()
    private let identifier = "hsk-ai.daily-study"

    func enable(hour: Int = 19, minute: Int = 0) async {
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
            guard granted else {
                permissionDenied = true
                enabled = false
                return
            }
            permissionDenied = false
            center.removePendingNotificationRequests(withIdentifiers: [identifier])
            let content = UNMutableNotificationContent()
            content.title = NSLocalizedString("reminder_notification_title", comment: "")
            content.body = NSLocalizedString("reminder_notification_body", comment: "")
            content.sound = .default
            content.userInfo = ["deepLink": "pomp-hsk-ai://course"]

            var components = DateComponents()
            components.hour = hour
            components.minute = minute
            let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
            try await center.add(UNNotificationRequest(identifier: identifier, content: content, trigger: trigger))
            enabled = true
            UserDefaults.standard.set(true, forKey: "studyReminderEnabled")
        } catch {
            enabled = false
        }
    }

    func disable() {
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
        enabled = false
        permissionDenied = false
        UserDefaults.standard.set(false, forKey: "studyReminderEnabled")
    }
}
