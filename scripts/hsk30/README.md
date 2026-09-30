# HSK 3.0 source extraction

This directory contains normalized source material extracted from the HSK 3.0 course books before runtime integration.

Current source:
- `HSK 3.0 PDF/新HSK教程1.pdf`
- N1 course outline: `nhsk1_course_outline.json`
- First verified lesson seed: `seed_nhsk1_lesson_01.py`

Rules:
- Keep the textbook Chinese dialogue and pinyin exactly as the source.
- Add UZ/RU/TJ as a separate translation layer.
- Keep proper nouns separate from the 300-word syllabus vocabulary count.
- Do not copy textbook exercise pages into runtime data; Course V3 will generate interactive exercises from vocabulary + grammar + dialogue.
- Record PDF/printed page provenance for every extracted lesson.


## N1 source audit

- `nhsk1_vocab_index.json` is a direct audit layer for the book's end-of-book vocabulary index (PDF pages 136-142).
- The common vocabulary index contains 307 rows. Eight are explicitly marked by the book as beyond the syllabus: 病人, 服务员, 机场, 接, 斤, 售货员, 药, 医.
- The proper-noun index contains 12 rows. Four recurring character names used in lesson dialogues are retained separately as allowed extras: 安妮, 白家月, 陈天中, 李文.
- The book also states that the course is aligned to 300 words. Because that publisher claim does not map transparently to the raw index row counts, the extraction preserves both facts rather than silently forcing the index to 300.
- `verify_nhsk1_source.py` checks exact common-word coverage, source proper nouns, allowed character-name extras, 15 lessons, 45 dialogue blocks, 203 dialogue lines, and 40 grammar points.
