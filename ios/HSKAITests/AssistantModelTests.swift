import XCTest
@testable import HSKAI
final class AssistantModelTests:XCTestCase{
 func testStatusEnvelopeAllowsOmittedCollections()throws{
  let data=Data(#"{"ok":true,"enabled":true}"#.utf8)
  let value=try JSONDecoder().decode(IOSAssistantEnvelope.self,from:data)
  XCTAssertTrue(value.ok);XCTAssertTrue(value.enabled == true);XCTAssertEqual(value.error,"");XCTAssertTrue(value.conversations.isEmpty);XCTAssertTrue(value.messages.isEmpty);XCTAssertEqual(value.nextCursor,"")
 }
}
