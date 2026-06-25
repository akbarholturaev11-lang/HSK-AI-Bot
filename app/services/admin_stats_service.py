from sqlalchemy import func, select

from app.db.models.user import User


async def miniapp_course_mode_stats_text(session) -> str:
    course_mode_users = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.learning_mode == "course")
        )
    ).scalar() or 0

    return (
        "📊 <b>Admin statistika</b>\n\n"
        "Mini App kurs rejimidagi foydalanuvchilar: "
        f"<b>{course_mode_users}</b>"
    )
