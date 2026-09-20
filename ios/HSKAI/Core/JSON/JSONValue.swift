import Foundation

enum JSONValue: Codable, Sendable, Equatable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unsupported JSON value"
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .int(let value): try container.encode(value)
        case .double(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }

    var stringValue: String? {
        guard case .string(let value) = self else { return nil }
        return value
    }

    var intValue: Int? {
        switch self {
        case .int(let value): return value
        case .double(let value) where value.rounded() == value: return Int(value)
        default: return nil
        }
    }

    var boolValue: Bool? {
        guard case .bool(let value) = self else { return nil }
        return value
    }

    var objectValue: [String: JSONValue]? {
        guard case .object(let value) = self else { return nil }
        return value
    }

    var arrayValue: [JSONValue]? {
        guard case .array(let value) = self else { return nil }
        return value
    }

    func localized(language: String) -> String {
        if let stringValue { return stringValue }
        guard let object = objectValue else { return "" }

        let language = language.lowercased()
        let primary: String
        switch language {
        case "uz": primary = "uz"
        case "tg", "tj": primary = "tj"
        default: primary = "ru"
        }

        for key in [primary, "ru", "uz", "tj"] {
            if let value = object[key]?.stringValue,
               !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return value
            }
        }
        return ""
    }
}

extension Dictionary where Key == String, Value == JSONValue {
    func string(_ key: String) -> String {
        self[key]?.stringValue ?? ""
    }

    func int(_ key: String) -> Int? {
        self[key]?.intValue
    }

    func bool(_ key: String) -> Bool? {
        self[key]?.boolValue
    }

    func object(_ key: String) -> [String: JSONValue]? {
        self[key]?.objectValue
    }

    func array(_ key: String) -> [JSONValue] {
        self[key]?.arrayValue ?? []
    }

    func localized(_ key: String, language: String) -> String {
        self[key]?.localized(language: language) ?? ""
    }
}
