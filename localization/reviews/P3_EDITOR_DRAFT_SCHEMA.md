# P3 editor translation drafts — private structural validator

This is an **editor-only, local verification contract**, not a translation
service, client runtime, lesson pack, or publish/approval workflow.

## Draft shape

Supply a JSON file outside public asset folders:

```json
{
  "schema_version": 1,
  "kind": "p3_editor_translation_draft",
  "source_file": "app/static/course_v3_data/nhsk2/lesson_16.json",
  "source_git_blob_sha1": "<copy the actual 40-character Git blob SHA from the P3 pointer report>",
  "translations": [
    {
      "pointer": "/grammar/0/examples/0/translation",
      "values": {
        "uz": "<human-reviewed Uzbek translation>",
        "ru": "<human-reviewed Russian translation>",
        "tj": "<human-reviewed Tajik translation>"
      }
    }
  ]
}
```

The values in angle brackets are **instructions, not valid translations**.
Human translators must author all three actual strings, then editors must
review their meaning and grammar. Never autofill them from other locales.

Use a source SHA pinned to the exact original lesson JSON bytes. The accepted
source path must be one existing file in the seven course directories. The
draft may contain a subset of approved missing display fields, but every
included field must provide all three original locales. Other keys, unsupported
languages, previously nonempty fields and assessment/answer paths are rejected.

## Run locally

```bash
python scripts/i18n_editor_translation_draft.py --draft /private/path/editor_draft.json
python -m unittest tests.test_i18n_editor_translation_draft
```

The CLI prints **only counts and pass/fail**. Do not attach source texts or
editorial drafts to public GitHub issues, Actions artifacts or static web pages.

The optional library function `preview_editor_draft(raw_source_bytes, draft)`
returns an **in-memory full source copy** with whitelisted translations; it must
never be published, persisted as a public asset, or returned by unauthenticated
APIs. `validate_editor_draft` returns count-only metadata. Neither one writes
course JSON or changes scoring/Pro/access behavior.

Structural acceptance is not semantic/human approval. Once an editor approves
the content independently, integrate reviewed values through the approved
content repository process, regenerate the source-bound hash, rerun the full
746-source audit and access/grade tests, and manually QA old/new clients.

Never change `correct_index`, `options`, `reverse_builder`,
`answer_tokens`, Chinese, pinyin, pricing, Pro entitlement, progress or
grade behavior in this workflow. P3 app runtime remains **NOT STARTED**.

## Check coverage across multiple private editor drafts

Keep each validated draft as a separate `.json` file in a **local private
folder outside the Git checkout**, for example `/private/editor-drafts/`.
These files hold unfinished translations and must **never** be uploaded to
`app/static`, a public repository path or GitHub Actions artifacts.

Run the safe, read-only coverage command after editing:

```bash
python scripts/i18n_editor_translation_batch.py --draft-dir /private/editor-drafts
python -m unittest tests.test_i18n_editor_translation_batch
```

The first command counts how many of the **272 missing display maps / 816
UZ/RU/TJ values** are covered by structurally valid drafts. A directory with
no drafts is a valid incomplete state: it reports all 816 values outstanding.
Multiple files may belong to one lesson **only when their JSON pointers do
not overlap**. Duplicate pointers, changed source SHA, missing locale values,
unauthorized answer fields, symlinks and files outside the draft format are
rejected; a failed batch has no partial-success report.

```bash
python scripts/i18n_editor_translation_batch.py \
  --draft-dir /private/editor-drafts --require-complete
```

The strict flag rejects any still-uncovered source display maps. Even a
structurally complete batch has `ready_to_ship: false`: the human language
review, approved content-repository integration, Pro/auth security, grade
regressions and real-device QA remain separate requirements.

The command prints **counts only**, never translated sentences, source
answers, Chinese or pinyin. It reads current original lessons but does not
modify them, generate a deployable pack or change the application runtime.

## Prove preview integrity before human approval

A structurally valid translation draft is NOT enough to allow applying an
edited lesson payload. The independent library-only invariant check compares
the original lesson with a proposed **in-memory** preview, restores only
explicitly whitelisted draft translation maps, then compares **all remaining
JSON fields and types** with the original. The check rejects modified
Chinese/pinyin, question options or their order, `correct_index`, builder
answer tokens, grading booleans/weights, embedded Pro flags, extra/missing
fields, unreviewed translations and even changing integer types to boolean.

```python
from scripts.i18n_editor_preview_integrity import (
    attest_editor_preview, verify_approved_preview,
)

# source_bytes = original raw lesson file bytes (trusted local editor only)
# draft = JSON object that has passed the private translator review workflow
proof = attest_editor_preview(source_bytes, draft)
assert proof["all_nonapproved_source_fields_unchanged"]
assert not proof["ready_to_ship"]

# Optional independent verification of a proposed private in-memory preview:
# proof = verify_approved_preview(source_bytes, draft, proposed_preview)
```

The returned proof contains only safe metadata, including Git source SHA and
the number of checked UZ/RU/TJ fields. It contains **no translations, answer
values or protected lesson content**. No public/Pro pack or file is generated,
and no app/runtime/API code is modified. This is an integrity proof **only**:
semantic language approval, paid-content/auth boundaries, and real-device
regressions still require separate review. P3 runtime remains NOT STARTED.
