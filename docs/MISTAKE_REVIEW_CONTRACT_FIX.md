# Mistake review listening contract

Status (2026-10-15 source audit): the missing-audio replay bug is fixed in
`CourseMistakeService._review_question`. The regression file
`tests/test_mistake_review_contract.py` passes all 10 tests. This records local
source behavior; it does not claim a separate production rollout.

## Current invariants

- A `listening_choice` mistake is replayable only when `audio_text` exists. A
  sentence alone cannot stand in for the audio prompt.
- Fill and dialog-cloze tasks need a visible sentence/context or playable audio.
- Listening prompts hide pinyin before the learner answers. Old records that
  copied the spoken answer into `sentence` have that duplicate answer removed.
- The immutable review-session snapshot preserves `material_version`,
  `material_ref`, `format`, `language`, and the interaction content required to
  replay the task.
- If required source material is missing or the format cannot be reproduced,
  the task is skipped instead of being converted into a different question.

Relevant source: `app/services/course_mistake_service.py`.

Verify after changing this contract:

```bash
venv_311/bin/python -m pytest tests/test_mistake_review_contract.py -q
```

A passing test checks the replay contract, not the production deployment.
