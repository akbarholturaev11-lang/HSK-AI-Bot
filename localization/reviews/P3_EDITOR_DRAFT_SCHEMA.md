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

## Prepare the first real editor worksheet — HSK 3.0 Level 2, lesson 16

This is an **editor-only local action**; work in a private, access-controlled
folder outside the Git checkout. The first affected source,
`app/static/course_v3_data/nhsk2/lesson_16.json`, has **six** blank grammar
example translation maps (18 UZ/RU/TJ text cells).

```bash
python scripts/i18n_grammar_editor_workspace.py \
  --track nhsk2 --lesson 16 \
  --private-dir /private/p3-lesson16-new-worksheet
```

The destination directory **must not exist yet**, and its parent must exist
outside the repository. The generator creates a private `worksheet.json`
containing exactly the six original grammar-example Chinese sentences,
the corresponding JSON pointers and original Git blob SHA. It also creates
`editor_draft.json` with six matching UZ/RU/TJ **empty values**.

The blank draft is *intentionally rejected* by the validator until a
translator writes all three genuine text values for each pointer.

```bash
python scripts/i18n_editor_translation_draft.py \
  --draft /private/p3-lesson16-new-worksheet/editor_draft.json
```

The directory is created with private (0700) permissions and both files are
created 0600 with exclusive create, never overwritten. No lesson JSON is
changed; the CLI prints **counts only**, not the Chinese example sentences,
answers or draft translations. Do not commit, upload, or share the worksheet
as a public lesson/course/CI artifact. Source context is for authorized
human language reviewers only. Structural validation and in-memory preview
integrity still require separate editorial signoff; P3 runtime NOT STARTED.

## Duplicate grammar card display fields: explicit review requirement

The existing Level 2 lesson 16 file stores six example translations twice:
- approved editor source: `/grammar/0/examples/{0..5}/translation`
- **derived mirror for course card display:**
  `/sections/1/cards/0/g/examples/{0..5}/translation`

The private `worksheet.json` now lists `mirrored_paths` alongside the
original Chinese example. **These are informational review locations only**;
the accompanying `editor_draft.json` must include *only* the whitelisted
`/grammar/...` pointers. Editor translations are authored only once.

Before integrating any approved content, a separate strictly reviewed source
adapter must synchronize matched mirrored display fields (after validating
original Chinese, original locale-map equality, grade/correct_index/options,
Pro access and client compatibility). The existing private preview integrity
checker intentionally rejects unapproved mirror edits. No synchronizer is
activated here. Do not treat a structurally valid draft as a working course
UI patch without this integration review.

## Verify mirrored grammar cards (private, in-memory only)

Some lessons embed duplicated `_grammar` cards. For example, HSK 3.0 Level
2 lesson 16 has **six original** `/grammar/.../translation` maps and **six
mirrored** `/sections/1/cards/0/g/examples/.../translation` maps. The editor
draft must still contain only the **six original grammar** JSON pointers: it
requires 18 UZ/RU/TJ values, **not 36 different translations**.

A separate preview proof finds the mirror positions from the **unchanged
source**, verifies identical original Chinese text and empty locale maps, and
applies each approved translation to **both** source-aligned display copies
inside a detached Python dictionary. Any changed `correct_index`, options,
builder tokens, grade, Pro/lock flag, pinyin, Chinese text, or mismatched mirror
is rejected by exact full-JSON comparison.

```python
from scripts.i18n_editor_grammar_mirror_integrity import (
    attest_mirrored_grammar_preview, verify_mirrored_grammar_preview,
)
proof = attest_mirrored_grammar_preview(original_source_bytes, approved_editor_draft)
assert proof["all_other_fields_unchanged"]
assert not proof["ready_to_ship"]
```

The preview object itself still contains whole lessons and grading material.
**Never write it to `app/static/`, public GitHub files, CI artifacts or
unauthenticated endpoints.** This check does not authorize updating the source,
payment/access gates, live runtime or human language sign-off.

## Reuse exact original grammar contexts in another lesson (editor-only)

The same original grammar examples can appear in multiple lessons. The source
deduplication audit confirmed 272 blank grammar maps but only 136 distinct
contexts. Reusing one HUMAN-REVIEWED translation is allowed only in a PRIVATE
editor draft when original grammar number, title, rule, Chinese and pinyin
all match byte-for-byte at the JSON value level. Context reuse is not
authorization to publish or merge lesson JSON.

Example for HSK 3.0 Level 2 lesson 20:

```bash
python scripts/i18n_editor_translation_reuse.py \
  --source-draft /private/lesson_16/editor_draft.json \
  --source-draft /private/lesson_17/editor_draft.json \
  --source-draft /private/lesson_18/editor_draft.json \
  --target-track nhsk2 --target-lesson 20 \
  --private-output-dir /private/new-lesson20-review
```

All source drafts must be private files outside Git checkout, and the output
directory must be new and private. The tool checks original/target source SHA,
approved grammar display paths, conflict-free texts and entire private mirror
preview integrity. It outputs two files: editor_draft.json (still UNAPPROVED)
and reuse_provenance.json (safe source refs/counts), never a public pack.
Even structurally valid drafts still need language review, auth/Pro and
graded-content QA. The original HSK JSON and runtime are unchanged.
