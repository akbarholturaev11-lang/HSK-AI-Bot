# Mistake review replay contract fix

## Problem
`Xatolarim` review can currently emit a listening task with answer options but without playable audio. The backend treats `sentence` as sufficient context for a listening prompt, while the Mini App only renders the audio control when `audio_text` exists.

## Root cause
In `CourseMistakeService._review_question` the current guard is effectively:

```python
if (needs_listen or needs_fill) and not sentence and not audio_text:
    return None
```

For `listening_choice`, a non-empty `sentence` therefore allows the question through even when `audio_text` is empty.

The immutable retry snapshot also drops interaction metadata (`format`, `language`, `material_version`, `material_ref`), so a retry cannot reliably validate or reproduce the original interaction contract.

## Required code change
Patch `app/services/course_mistake_service.py`:

1. Listening tasks MUST require `audio_text`; a sentence is never a substitute for audio.
2. Fill/dialog tasks may continue to require their visible sentence/context as appropriate.
3. Preserve these fields in `_review_session_question`:
   - `material_version`
   - `material_ref`
   - `format`
   - `language`
4. Never issue an unanswerable task. If required material is missing, skip it and select another mistake from the candidate pool.

Recommended guard:

```python
if needs_listen and not audio_text:
    return None
if needs_fill and not sentence and not audio_text:
    return None
```

Recommended snapshot additions:

```python
"material_version": int(question.get("material_version") or MISTAKE_REVIEW_MATERIAL_VERSION),
"material_ref": cls._text(question.get("material_ref"), 160),
"format": cls._text(question.get("format"), 64),
"language": cls._language(question.get("language")),
```

## Regression tests
`tests/test_mistake_review_contract.py` was added and must pass. It locks three invariants:

- listening + sentence + no audio => not reviewable;
- listening + audio => audio preserved and pinyin hidden before answer;
- retry snapshot preserves the interaction contract.

## Local validation
Run on `codex/local-ai` after syncing this cloud branch:

```bash
python -m unittest tests.test_mistake_review_contract tests.test_course_mistake_service
python -m py_compile app/services/course_mistake_service.py
graphify update .
```

Then verify the Mini App manually:

- open `Xatolarim`;
- start review containing a listening mistake;
- confirm the audio button is present and speaks the original `audio_text`;
- confirm no listening question can be shown without audio;
- retry the same review and confirm the same interaction type/material is preserved.

## Branch discipline
Cloud changes stay on `codex/cloud-ai` until local tests pass. Do not push this contract change to `main` before validation.
