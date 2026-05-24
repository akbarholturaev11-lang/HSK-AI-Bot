import asyncio

from sqlalchemy import select

from app.db.models.course_lessons import CourseLesson
from app.db.session import async_session_maker as SessionLocal
from scripts.hsk4_upper_pdf_materials import apply_hsk4_upper_pdf_materials


LESSON = apply_hsk4_upper_pdf_materials(
    {
        "level": "hsk4",
        "lesson_order": 9,
        "lesson_code": "HSK4-L09",
        "title": "",
        "goal": "{}",
        "intro_text": "{}",
        "vocabulary_json": "[]",
        "dialogue_json": "[]",
        "grammar_json": "[]",
        "exercise_json": "[]",
        "answers_json": "[]",
        "homework_json": "[]",
        "review_json": "[]",
        "is_active": True,
    }
)


async def upsert_lesson():
    async with SessionLocal() as session:
        result = await session.execute(
            select(CourseLesson).where(CourseLesson.lesson_code == LESSON["lesson_code"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in LESSON.items():
                setattr(existing, key, value)
            print(f"updated: {LESSON['lesson_code']}")
        else:
            session.add(CourseLesson(**LESSON))
            print(f"inserted: {LESSON['lesson_code']}")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(upsert_lesson())
