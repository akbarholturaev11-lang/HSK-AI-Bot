# HSK AI iOS

Native SwiftUI client for HSK AI.

## Current state

Phase 0 foundation:
- SwiftUI application target definition
- central production API environment
- origin-guarded HTTPS API client
- Keychain credential storage

No Android, desktop or Mini App runtime code is reused inside the client. Business state remains server-authoritative.

## Generate the Xcode project

This folder uses XcodeGen so the project structure stays reviewable and does not depend on hand-edited `.pbxproj` files.

```bash
cd ios
brew install xcodegen   # once
xcodegen generate
open HSKAI.xcodeproj
```

The generated `HSKAI.xcodeproj` is intentionally ignored.

## Build target

- Product: HSK AI
- Bundle ID: `com.pomp.hskai`
- Deployment target: iOS 17.0+
- API origin: `https://telegram-chinese-bot-production.up.railway.app`

The API origin is public configuration, not a secret. Authentication credentials must remain in Keychain.
