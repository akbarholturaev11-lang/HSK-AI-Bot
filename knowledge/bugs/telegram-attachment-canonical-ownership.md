# Keep historical native rows visible after attaching Telegram

Provider-first accounts create AI budgets, usage and Voice sessions with their
canonical `user_id` and NULL optional Telegram metadata. Attaching a real
Telegram identity later must not reset budgets, hide Voice history or bypass
daily limits through legacy integer callers.

`owner_clause` resolves a positive Telegram argument to the current canonical
User using an indexed scalar subquery. Canonical ownership takes precedence;
only rows without a canonical owner may use the legacy Telegram fallback.
Another account's stale matching Telegram metadata never authorizes its data.
Do not bulk-rewrite historical transport metadata to make ownership work.

`tests/test_telegram_link_acceptance.py` reproduces both missing native history
and foreign canonical access with the prior query, then verifies the fix. It
also exercises Google/Apple-first attachment through the real API and explicit
bot-proof services, preserving paid/learning/referral/budget snapshots and
checking Mini App/Windows/macOS share the same account afterward.
