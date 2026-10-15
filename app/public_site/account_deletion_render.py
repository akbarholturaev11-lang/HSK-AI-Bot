"""Public account-deletion instructions and ownership-verification interface."""


def render_account_deletion() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Delete your HSK AI account</title><meta name="robots" content="index,follow">
<style>
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:32px auto;padding:0 max(20px,env(safe-area-inset-left)) max(32px,env(safe-area-inset-bottom));line-height:1.6;color:#211d17;background:#fcfaf7}
h1,h2,h3{line-height:1.25}h1{font-size:clamp(1.65rem,5vw,2.1rem)}h2{font-size:1.2rem}a{color:#9d321c}button,.verification-link{font:inherit;min-height:48px;padding:10px 16px;border:1px solid #b8aba0;border-radius:10px;background:white;color:#211d17;cursor:pointer}button:disabled{opacity:.55;cursor:default}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #9d321c;outline-offset:3px}
.panel{padding:20px;border:1px solid #d6cec3;border-radius:16px;background:white;margin:24px 0}.providers{display:flex;gap:10px;flex-wrap:wrap}.providers button{flex:1;min-width:120px}.primary{background:#9d321c;color:white;border-color:#9d321c;width:100%;margin-top:16px}.secondary{margin-top:12px}.muted{color:#60584e;font-size:.94rem}.error{color:#8a2518;padding:12px;border:1px solid #e7b5a9;border-radius:10px}.verification-link{display:inline-block;margin-top:8px}.check{display:flex;align-items:flex-start;gap:12px}.check input{width:20px;height:20px;flex-shrink:0;margin-top:4px}.receipt{overflow-wrap:anywhere}dt{font-weight:600}dd{margin:0 0 12px}[hidden]{display:none!important}li{margin-bottom:8px}
</style><script src="/public-assets/account-deletion.js" defer></script></head>
<body><main><h1>Request deletion of your HSK AI account</h1>
<p>HSK AI is published by Pomp HSK AI. Your account is shared by the Android app, Telegram bot, Mini App and desktop clients. Deleting the app or unlinking a device does not delete the account.</p>
<section class="panel" aria-labelledby="request-title"><h2 id="request-title">1. Verify that you own the account</h2>
<p>Choose a sign-in method already linked to your HSK AI account. Use the same Google, Apple or Telegram identity you used in HSK AI. Email addresses are not used to find or merge accounts.</p>
<p class="muted">You do not need to reinstall HSK AI. Keep this page open, finish verification in the new tab or Telegram, then return here to confirm your request. Verification expires after 10 minutes.</p>
<div id="deletion-providers" class="providers" hidden>
<button type="button" data-provider="google" disabled>Google</button>
<button type="button" data-provider="apple" disabled>Apple</button>
<button type="button" data-provider="telegram" disabled>Telegram</button></div>
<p id="deletion-status" role="status" aria-live="polite">Verify ownership before confirming deletion. The instructions below also cover Telegram requests.</p>
<p id="deletion-error" class="error" role="alert" hidden></p>
<div id="deletion-pending" hidden><p id="deletion-instructions"></p>
<a id="deletion-verification-link" class="verification-link" target="_blank" rel="noopener noreferrer">Open verification</a></div>
<form id="deletion-confirm" hidden><h3>2. Confirm your deletion request</h3>
<p>Verified account: <strong id="deletion-account"></strong></p>
<label class="check"><input id="deletion-consent" type="checkbox" required><span>I request deletion of this whole shared HSK AI account and its associated data. I understand the retention rules below and that I must cancel any external store subscription separately.</span></label>
<button id="deletion-submit" class="primary" type="submit" disabled>Request account deletion</button></form>
<section id="deletion-receipt" class="receipt" aria-labelledby="receipt-title" hidden><h3 id="receipt-title">Deletion request received</h3>
<p id="deletion-receipt-message">Your request has been saved. No account data is deleted immediately.</p>
<dl><dt>Request reference</dt><dd id="deletion-reference"></dd><dt>Received</dt><dd id="deletion-requested-at"></dd><dt>Processing target</dt><dd id="deletion-due-at"></dd></dl>
<p id="deletion-completed-at" hidden></p>
<button id="deletion-check-status" class="secondary" type="button" hidden>Check request status</button>
<p class="muted">Status checking is available while this page session stays open. Closing or reloading the page clears its verification proof; keep the request reference to contact support. Completion status is retained for 30 days after processing.</p>
<p class="muted">We aim to process requests within 30 days. Support will explain any exceptional retention.</p></section>
<button id="deletion-retry" class="secondary" type="button" hidden>Retry</button>
<button id="deletion-restart" class="secondary" type="button" hidden>Choose another sign-in method</button>
<noscript><p>JavaScript is needed for Google or Apple verification on this page. Enable it and reload. Telegram users can also open the <a href="https://t.me/darsi_chini_bot?start=account_deletion">official HSK AI Telegram bot</a> and tap <strong>O‘chirishni so‘rash</strong> (Request deletion). This sends an explicit request, not an immediate deletion.</p></noscript>
</section>
<h2>How your request is handled</h2>
<p>Verification alone does not submit a request. After verification, review the account and explicitly confirm deletion. We aim to process confirmed requests within 30 days. Support reviews exceptional legal or security retention individually. Do not send passwords or identity documents to HSK AI or support.</p>
<h2>What will be deleted and retained</h2>
<ul><li>Your shared account, profile, linked Telegram/Google/Apple sign-in identities, authentication sessions and devices, learning progress, mistakes and voice activity are deleted across HSK AI services.</li>
<li>Pending and rejected payment records are removed. Approved payment records and required accounting and partner-payout facts are retained under the existing financial retention rules. Related partner payout evidence, payout details and ledger notes may also remain. Support reviews personal details in those records for legal or accounting retention exceptions and explains the applicable reason and period.</li>
<li>If legal, security or fraud-prevention obligations require exceptional retention, support explains the reason and applicable period when handling your request.</li></ul>
<p><strong>Account deletion does not cancel automatic renewal of subscriptions purchased through Google Play, Apple or another external store.</strong> Cancel those subscriptions in the store separately.</p>
<p>If a linked sign-in method is unavailable or you cannot verify your account, use Support in HSK AI or the official Telegram bot <a href="https://t.me/darsi_chini_bot">@darsi_chini_bot</a>. Support must verify ownership before processing a request.</p>
<p>See the <a href="/privacy">privacy policy</a> for how your data is used.</p>
</main></body></html>"""
