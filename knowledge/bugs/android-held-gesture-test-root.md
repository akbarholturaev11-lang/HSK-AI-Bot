# Finish a held Compose test gesture through its stable owner root

- Cause: the API35 Play carousel test reselected profile-promo-pager to release a held finger. That dynamic semantics lookup failed while the pager was laying out; failure rendering then accessed SnapshotStateObserver on the instrumentation thread. The CI XML identifies the final performTouchInput(up) line, not the card-position assertion.
- Fix: retain the resolved card coordinates for the before/held comparison on the UI thread. Finish through onRoot(), whose shared input owner retains the pointer state across targets, and release in finally. This uses the existing public Compose test API.
- Risk: instrumentation only; no product carousel/gesture code changes.
- Prevention: preserve the actual drag, frame advancement and >25px position assertion before release. Run the affected case in Direct and Play; keep the complete API35 CI gate enabled. Never replace this with a completed swipe that could hide a broken live drag.
