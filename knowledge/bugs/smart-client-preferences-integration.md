# Smart preferences must be tested through actual clients

- Sabab: service and widget tests preseeded canonical preferences. They missed
  that the real native study switch only wrote local state and neither actual
  client supplied missing IANA metadata, leaving first-use accounts unknown.
- Fix: connect the existing native switch to P1 device CAS/receipts, reconcile
  current server state and initialize only missing actual-zone metadata.
  Persist explicit intents for offline retries; global OFF and existing
  manual/other-channel choices remain authoritative. Browser automatic writes
  use the existing private runtime/held-account gate.
- Risk: lost acknowledgements, reversed ON/OFF responses, account replacement
  and an older widget frame must not restore revoked intent or personal data.
- Prevention: native bridge plus real Retrofit tests, actual extracted browser
  helper/map tests and authenticated backend fixtures starting with no Smart
  rows cover first use, exact retry, offline OFF, fresh revision/context floors,
  default-off zero-SQL exposure and unchanged source/channel ownership. Keep
  physical provider/device acceptance distinct from these automated checks.
