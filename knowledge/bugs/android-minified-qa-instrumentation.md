# Minified QA instrumentation needs its host runtime ABI

- Cause: `AndroidJUnitRunner.onCreate` loads shared support APIs from the
  target app. R8 can inline/remove tracing/Kotlin facades from a release app
  while the test APK excludes the duplicate dependency. Both signed QA variants
  crashed with missing `androidx.tracing.Trace`, then `kotlin.LazyKt`, before
  any test or native authentication ran.
- Fix: only the explicit `qaRelease` build type loads
  `android/app/qa-host-proguard-rules.pro`, retaining the shared runtime ABI
  and explicit test entry points, with method-body optimization allowed. A
  separate QA test rules file retains the reflected JUnit test/runner. Keep
  minification, resource shrinking, non-debuggable status and normal release
  ProGuard rules intact.
- Risk: a green APK build or debug instrumentation does not prove that the
  signed, minified instrumentation runner starts. Do not weaken production
  shrinking or TLS/authentication to repair this test-host problem.
- Prevention: run `SmartStudySignedStagingTest` with both signed Direct/Play QA
  APKs and matching test APKs. Check actual OS/journal outcomes and process
  restart; check package identity, signer and non-debuggable manifests first.
  This test is explicitly skipped outside the opt-in QA release variant.

Related upstream context: [AndroidX Test minification issue 2167](https://github.com/android/android-test/issues/2167).
The concrete missing classes above come from the local signed-device crash
logs; do not apply a broad production keep rule based on this test-only issue.

If a run fails after possible authentication or a grant, preserve its Keystore,
journal and server ledger. Inspect both device logs before continuing; never
reset/reseed or reuse an initial refresh proof to make a rerun pass.
