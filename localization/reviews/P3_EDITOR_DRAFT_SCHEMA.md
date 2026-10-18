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
