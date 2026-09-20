import Foundation
import Security

protocol CredentialStore: Sendable {
    func installationKey() throws -> String
    func refreshToken() throws -> String?
    func saveRefreshToken(_ token: String) throws
    func clearSession() throws
    func clearEverything() throws
}

/// The only persistent native-auth storage.
///
/// The short-lived access token deliberately never touches disk. Keychain
/// contains only the stable installation identity and the rotating refresh
/// token, matching the Android security contract.
struct KeychainCredentialStore: CredentialStore {
    private let service: String

    init(service: String = "com.pomp.hskai.auth") {
        self.service = service
    }

    func installationKey() throws -> String {
        if let existing = try read(account: Account.installationKey.rawValue) {
            return existing
        }

        var bytes = [UInt8](repeating: 0, count: 48)
        let status = bytes.withUnsafeMutableBytes { buffer in
            guard let baseAddress = buffer.baseAddress else {
                return errSecParam
            }
            return SecRandomCopyBytes(kSecRandomDefault, buffer.count, baseAddress)
        }
        guard status == errSecSuccess else {
            throw KeychainError.random(status)
        }

        let generated = Data(bytes)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")

        try write(generated, account: Account.installationKey.rawValue)
        return generated
    }

    func refreshToken() throws -> String? {
        try read(account: Account.refreshToken.rawValue)
    }

    func saveRefreshToken(_ token: String) throws {
        guard !token.isEmpty else {
            throw KeychainError.invalidPayload
        }
        try write(token, account: Account.refreshToken.rawValue)
    }

    func clearSession() throws {
        try delete(account: Account.refreshToken.rawValue)
    }

    func clearEverything() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.delete(status)
        }
    }

    private func read(account: String) throws -> String? {
        var query = baseQuery(account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess, let data = item as? Data else {
            throw KeychainError.read(status)
        }
        guard let value = String(data: data, encoding: .utf8), !value.isEmpty else {
            throw KeychainError.invalidPayload
        }
        return value
    }

    private func write(_ value: String, account: String) throws {
        guard let data = value.data(using: .utf8) else {
            throw KeychainError.invalidPayload
        }

        let query = baseQuery(account: account)
        let update = [kSecValueData as String: data]
        let updateStatus = SecItemUpdate(query as CFDictionary, update as CFDictionary)

        if updateStatus == errSecSuccess {
            return
        }
        guard updateStatus == errSecItemNotFound else {
            throw KeychainError.write(updateStatus)
        }

        var create = query
        create[kSecValueData as String] = data
        create[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let addStatus = SecItemAdd(create as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            throw KeychainError.write(addStatus)
        }
    }

    private func delete(account: String) throws {
        let status = SecItemDelete(baseQuery(account: account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.delete(status)
        }
    }

    private func baseQuery(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    private enum Account: String {
        case installationKey = "installation-key"
        case refreshToken = "refresh-token"
    }
}

enum KeychainError: Error, Equatable {
    case read(OSStatus)
    case write(OSStatus)
    case delete(OSStatus)
    case random(OSStatus)
    case invalidPayload
}
