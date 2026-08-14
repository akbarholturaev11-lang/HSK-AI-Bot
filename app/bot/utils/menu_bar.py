"""Chatdagi menyu barni (reply keyboard) yetkazish.

Muammo: kurs yo'lidan kirgan user menyu barni umuman ko'rmasdi. Kursga kirish
xabari rasm + inline WebApp tugmasi bilan ketadi, inline keyboard esa reply
keyboard yaratmaydi. Telegram bitta xabarga ikkalasini birga qo'yishga ruxsat
bermaydi, shuning uchun menyu alohida qisqa xabar bilan yuboriladi.

Reply keyboard bir marta o'rnatilgach chatda doimiy qoladi, shuning uchun
`once=True` bilan takror yuborilmaydi. `/start` esa userning ochiq harakati —
u yerda `once=False`, ya'ni menyu har safar tiklanadi.
"""

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.utils.i18n import t
from app.repositories.message_repo import MessageRepository


MENU_HINT_CONTENT_TYPE = "menu_hint"


async def send_menu_bar(
    *,
    session,
    user,
    respond,
    lang: str | None = None,
    once: bool = False,
) -> bool:
    """Menyu barni yuboradi. Yuborilgan bo'lsa True qaytaradi.

    `once=True` — ilgari yuborilgan bo'lsa hech narsa qilmaydi (Mini App
    yopilishi kabi avtomatik ilgaklar uchun).
    """
    if user is None:
        return False

    lang = lang or (getattr(user, "language", None) or "ru")
    repo = MessageRepository(session)

    if once:
        try:
            already_sent = await repo.get_latest_by_content_type(
                user_id=user.id,
                content_type=MENU_HINT_CONTENT_TYPE,
            )
        except Exception:
            already_sent = None
        if already_sent:
            return False

    try:
        await respond(
            t("menu_bar_hint", lang),
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        return False

    # `role="system"`: `qa_service` history filtri faqat user/assistant ni
    # oladi, ya'ni bu xizmat xabari AI promptiga tushmaydi.
    try:
        await repo.create(
            user_id=user.id,
            role="system",
            content=MENU_HINT_CONTENT_TYPE,
            content_type=MENU_HINT_CONTENT_TYPE,
        )
        await session.commit()
    except Exception:
        pass

    return True
