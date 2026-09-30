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
