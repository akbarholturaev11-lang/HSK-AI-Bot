import Foundation
import Security

struct NativeCredentials: Codable, Equatable, Sendable {
    let accessToken: String
    let refreshToken: String
}

protocol CredentialStore: Sendable {
    func load() throws -> NativeCredentials?
    func save(_ credentials: NativeCredentials) throws
    func clear() throws
}

struct KeychainCredentialStore: CredentialStore {
    private let service: String
    private let account: String

    init(
        service: String = "com.pomp.hskai.auth",
        account: String = "native-session"
    ) {
        self.service = service
        self.account = account
    }

    func load() throws -> NativeCredentials? {
        var query = baseQuery
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

        do {
            return try JSONDecoder().decode(NativeCredentials.self, from: data)
        } catch {
            throw KeychainError.invalidPayload
        }
    }

    func save(_ credentials: NativeCredentials) throws {
        let data: Data
        do {
            data = try JSONEncoder().encode(credentials)
        } catch {
            throw KeychainError.invalidPayload
        }

        var query = baseQuery
        let update = [kSecValueData as String: data]
        let updateStatus = SecItemUpdate(query as CFDictionary, update as CFDictionary)

        if updateStatus == errSecSuccess {
            return
        }
        guard updateStatus == errSecItemNotFound else {
            throw KeychainError.write(updateStatus)
        }

        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let addStatus = SecItemAdd(query as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            throw KeychainError.write(addStatus)
        }
    }

    func clear() throws {
        let status = SecItemDelete(baseQuery as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.delete(status)
        }
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

enum KeychainError: Error, Equatable {
    case read(OSStatus)
    case write(OSStatus)
    case delete(OSStatus)
    case invalidPayload
}
