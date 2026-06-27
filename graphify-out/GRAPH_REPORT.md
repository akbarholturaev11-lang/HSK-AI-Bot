# Graph Report - telegram_chinese_bot_clean  (2026-05-13)

## Corpus Check
- 266 files · ~530,587 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2333 nodes · 5338 edges · 45 communities detected
- Extraction: 56% EXTRACTED · 44% INFERRED · 0% AMBIGUOUS · INFERRED: 2346 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]

## God Nodes (most connected - your core abstractions)
1. `UserRepository` - 116 edges
2. `add()` - 84 edges
3. `t()` - 73 edges
4. `CourseLesson` - 68 edges
5. `CourseEngineService` - 51 edges
6. `handle_text_message()` - 49 edges
7. `Response` - 47 edges
8. `run_course_entry_flow()` - 44 edges
9. `build_from_json()` - 43 edges
10. `Request` - 42 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `text()`  [INFERRED]
  check_tables.py → graphify/worked/httpx/raw/models.py
- `clean()` --calls--> `text()`  [INFERRED]
  full_clean.py → graphify/worked/httpx/raw/models.py
- `run_course_entry_flow()` --calls--> `create()`  [INFERRED]
  app/bot/handlers/course.py → graphify/tests/fixtures/sample.ex
- `discount_confirm()` --calls--> `create()`  [INFERRED]
  app/bot/handlers/admin_discount.py → graphify/tests/fixtures/sample.ex
- `handle_text_message()` --calls--> `create()`  [INFERRED]
  app/bot/handlers/messages.py → graphify/tests/fixtures/sample.ex

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (212): _check_tree_sitter_version(), _csharp_extra_walk(), extract(), extract_blade(), extract_c(), extract_cpp(), extract_csharp(), extract_dart() (+204 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (143): admin_deleteuser_handler(), delete_user_command(), command_language_callback_handler(), command_language_keyboard(), command_level_callback_handler(), command_level_keyboard(), help_command_handler(), invite_command_handler() (+135 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (101): Exception, Auth, BasicAuth, BearerAuth, DigestAuth, NetRCAuth, Authentication handlers. Auth objects are callables that modify a request before, Load credentials from ~/.netrc based on the request host. (+93 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (157): _cross_community_surprises(), _cross_file_surprises(), _file_category(), god_nodes(), graph_diff(), _is_concept_node(), _is_file_node(), _node_community_map() (+149 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (108): add(), build_graph(), Graph, build_from_json(), Build a NetworkX graph from an extraction dict.      directed=True produces a Di, attach_hyperedges(), Store hyperedges in the graph's metadata dict., admin_stats_handler() (+100 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (165): _git_root(), _hooks_dir(), install(), _install_hook(), Walk up to find .git directory., Return the git hooks directory, respecting core.hooksPath if set (e.g. Husky)., Install a single git hook, appending if an existing hook is present., Remove graphify section from a git hook using start/end markers. (+157 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (32): MyApp.Accounts.User, create(), validate(), OnboardingStates, handle_image_message(), cmd_start(), _get_demo_lesson(), process_language() (+24 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (100): _detect_url_type(), _download_binary(), _fetch_arxiv(), _fetch_html(), _fetch_tweet(), _fetch_webpage(), _html_to_markdown(), ingest() (+92 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (91): collect_files(), extract_python(), Extract classes, functions, and imports from a .py file via tree-sitter AST., _status_label(), course_homework_keyboard(), course_reminder_notification_keyboard(), next_study_time_inline_keyboard(), Keyingi o'qish vaqtini tanlash — inline tugmalar (ReplyKeyboard o'rniga). (+83 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (59): Base, Base, DeclarativeBase, AdminAudioStates, BroadcastStates, DiscountStates, admin_audio_list_handler(), admin_broadcast_handler() (+51 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (59): bc_activity_filter(), bc_cancel(), bc_confirm(), bc_discount_filter(), bc_enter_text(), bc_lang_filter(), bc_level_filter(), bc_mode_filter() (+51 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (67): handle_delete(), handle_enrich(), handle_get(), handle_list(), handle_search(), handle_upload(), API module - exposes the document pipeline over HTTP. Thin layer over parser, va, Accept a list of file paths, run the full pipeline on each,     and return a sum (+59 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (70): Enum, classify_file(), convert_office_file(), count_words(), detect(), detect_incremental(), docx_to_markdown(), extract_pdf_text() (+62 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (53): area(), Analyzer, compute_score(), normalize(), Fixture: functions and methods that call each other - for call-graph extraction, run_analysis(), Circle, Color (+45 more)

### Community 14 - "Community 14"
Cohesion: 0.04
Nodes (29): _background_scheduler(), lifespan(), Run all lesson seed scripts in the background after startup., _seed_lessons(), BaseMiddleware, create_bot(), main(), _ensure_bootstrap_columns() (+21 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (19): ApiClient, CacheManager, Config, createProcessor(), DataProcessor, Get-Data(), GraphifyDemo, HttpClient (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (51): Return the first path component - used to detect cross-repo edges., Score how surprising a cross-file edge is. Returns (score, reasons)., _surprise_score(), _top_level_dir(), _community_article(), _cross_community_links(), _god_node_article(), _index_md() (+43 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (16): admin_giveaccess_handler(), admin_payment_approve_handler(), admin_payment_reject_handler(), admin_payment_reject_reason_select_handler(), admin_payment_reject_with_reason_handler(), _is_night(), payment_screenshot_handler(), _waiting_message() (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (44): find(), _body_content(), cache_dir(), cached_files(), check_semantic_cache(), clear_cache(), file_hash(), load_cached() (+36 more)

### Community 19 - "Community 19"
Cohesion: 0.1
Nodes (26): build(), build_merge(), deduplicate_by_label(), _norm_label(), _normalize_id(), Merge multiple extraction results into one graph.      directed=True produces a, Canonical dedup key — lowercase, alphanumeric only., Merge nodes that share a normalised label, rewriting edge references.      Prefe (+18 more)

### Community 20 - "Community 20"
Cohesion: 0.19
Nodes (22): _estimate_tokens(), print_benchmark(), _query_subgraph_tokens(), Token-reduction benchmark - measures how much context graphify saves vs naive fu, Print a human-readable benchmark report., Run BFS from best-matching nodes and return estimated tokens in the subgraph con, Measure token reduction: corpus tokens vs graphify query tokens.      Args:, run_benchmark() (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (15): check_update(), _notify_only(), Check for pending semantic update flag and notify the user if set.      Cron-saf, Write a flag file and print a notification (fallback for non-code-only corpora)., Tests for watch.py - file watcher helpers (no watchdog required)., check_update returns True and is silent when needs_update flag is absent., check_update returns True and prints notification when flag exists., check_update never removes the needs_update flag (clearing is LLM's job). (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.43
Nodes (6): EventServiceProvider, NotifyAdmins, OrderPlaced, SendWelcomeEmail, ShipOrder, UserRegistered

### Community 23 - "Community 23"
Cohesion: 0.53
Nodes (4): Get-PyVenvConfig(), global:deactivate(), global:_OLD_VIRTUAL_PROMPT(), global:prompt()

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): Animal, -initWithName, -speak, Dog, -fetch

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (4): AppServiceProvider, CashierGateway, PaymentGateway, StripeGateway

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (2): run_async_migrations(), run_migrations_online()

### Community 27 - "Community 27"
Cohesion: 0.6
Nodes (2): ColorResolver, DefaultPalette

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (2): Settings, BaseSettings

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (1): add daily limit offer sent at  Revision ID: 0005 Revises: 0004 Create Date: 2026

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (1): add course_audio table for storing telegram file_ids  Revision ID: 0015_add_cour

### Community 31 - "Community 31"
Cohesion: 0.5
Nodes (1): add trial dates to users  Revision ID: 0004 Revises: 0003 Create Date: 2026-03-2

### Community 32 - "Community 32"
Cohesion: 0.5
Nodes (1): add reminder_prompt_count to course_progress  Revision ID: 0014_add_reminder_pro

### Community 33 - "Community 33"
Cohesion: 0.5
Nodes (1): add weekly progress fields  Revision ID: 0017_add_weekly_progress_fields Revises

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (1): add course_promo_sent to users  Revision ID: 0016_add_course_promo_sent Revises:

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (1): add selected plan type to users  Revision ID: 0008 Revises: 0007 Create Date: 20

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (1): add referrals and user discount fields  Revision ID: 0003 Revises: 0002 Create D

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (1): add expiry reminder sent at to users  Revision ID: 0010 Revises: 0009 Create Dat

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): add discount progress fields to users  Revision ID: 0007 Revises: 0006 Create Da

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): add payment message ids for cleanup on approve  Revision ID: 0012_add_payment_ms

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): add bonus questions used to users  Revision ID: 0009 Revises: 0008 Create Date:

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (1): add reminder_tz_offset and last_reminder_sent_at to course_progress  Revision ID

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (1): initial migration  Revision ID: 0001 Revises: Create Date: 2026-03-24

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (1): Transformer

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (1): graphify - extract · build · cluster · analyze · report.

## Knowledge Gaps
- **389 isolated node(s):** `AI tutor javobidan keyin: 'Tushundim' → keyingi bo'limga o'tish.`, `Shown while waiting for 3 referrals — only back button.`, `Shown when 3/3 referrals reached — plan buttons + back.`, `lesson.title oddiy string yoki JSON bo'lishi mumkin — xitoycha qismini qaytaradi`, `V2 darslar uchun universal 'Davom etamiz' tugmasi (audiosiz).` (+384 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 26`** (5 nodes): `do_run_migrations()`, `env.py`, `run_async_migrations()`, `run_migrations_offline()`, `run_migrations_online()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (5 nodes): `ColorResolver`, `.accent()`, `.primary()`, `DefaultPalette`, `sample_php_static_prop.php`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (4 nodes): `admin_id_list()`, `config.py`, `Settings`, `BaseSettings`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (4 nodes): `0005_add_daily_limit_offer_sent_at.py`, `downgrade()`, `add daily limit offer sent at  Revision ID: 0005 Revises: 0004 Create Date: 2026`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (4 nodes): `0015_add_course_audio.py`, `downgrade()`, `add course_audio table for storing telegram file_ids  Revision ID: 0015_add_cour`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (4 nodes): `0004_add_trial_dates_to_users.py`, `downgrade()`, `add trial dates to users  Revision ID: 0004 Revises: 0003 Create Date: 2026-03-2`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (4 nodes): `0014_add_reminder_prompt_count.py`, `downgrade()`, `add reminder_prompt_count to course_progress  Revision ID: 0014_add_reminder_pro`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (4 nodes): `0017_add_weekly_progress_fields.py`, `downgrade()`, `add weekly progress fields  Revision ID: 0017_add_weekly_progress_fields Revises`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (4 nodes): `0016_add_course_promo_sent.py`, `downgrade()`, `add course_promo_sent to users  Revision ID: 0016_add_course_promo_sent Revises:`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (4 nodes): `0008_add_selected_plan_type_to_users.py`, `downgrade()`, `add selected plan type to users  Revision ID: 0008 Revises: 0007 Create Date: 20`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (4 nodes): `0003_add_referrals_and_user_discount_fields.py`, `downgrade()`, `add referrals and user discount fields  Revision ID: 0003 Revises: 0002 Create D`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (4 nodes): `0010_add_expiry_reminder_sent_at_to_users.py`, `downgrade()`, `add expiry reminder sent at to users  Revision ID: 0010 Revises: 0009 Create Dat`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (4 nodes): `0007_add_discount_progress_fields_to_users.py`, `downgrade()`, `add discount progress fields to users  Revision ID: 0007 Revises: 0006 Create Da`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (4 nodes): `0012_add_payment_msg_ids.py`, `downgrade()`, `add payment message ids for cleanup on approve  Revision ID: 0012_add_payment_ms`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (4 nodes): `0009_add_bonus_questions_used_to_users.py`, `downgrade()`, `add bonus questions used to users  Revision ID: 0009 Revises: 0008 Create Date:`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (4 nodes): `0013_add_reminder_tz_and_last_sent.py`, `downgrade()`, `add reminder_tz_offset and last_reminder_sent_at to course_progress  Revision ID`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (4 nodes): `0001_initial.py`, `downgrade()`, `initial migration  Revision ID: 0001 Revises: Create Date: 2026-03-24`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (4 nodes): `Transformer`, `.forward()`, `.__init__()`, `sample.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (3 nodes): `__init__.py`, `__getattr__()`, `graphify - extract · build · cluster · analyze · report.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `add()` connect `Community 4` to `Community 0`, `Community 1`, `Community 3`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 15`, `Community 20`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `_extract_generic()` connect `Community 0` to `Community 8`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `UserRepository` connect `Community 1` to `Community 6`, `Community 9`, `Community 10`, `Community 14`, `Community 17`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `UserRepository` (e.g. with `User` and `Message`) actually correct?**
  _`UserRepository` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 98 inferred relationships involving `str` (e.g. with `_ensure_bootstrap_columns()` and `format_intro()`) actually correct?**
  _`str` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 82 inferred relationships involving `add()` (e.g. with `.create()` and `.create()`) actually correct?**
  _`add()` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 72 inferred relationships involving `t()` (e.g. with `course_review_offer_keyboard()` and `course_satisfaction_keyboard()`) actually correct?**
  _`t()` has 72 INFERRED edges - model-reasoned connections that need verification._