"""Shaxsiy takror (UIUX-007) jadvalining Xatolarim bilan umumiy qismi.

Alohida modul: `course_mistake_service` adaptive servisni import qilmasdan
yakuniy tekshiruv sanasini belgilashi uchun (aylanma importsiz).
"""

from datetime import date, datetime, timedelta

# Xatolarimda yopilgandan keyin oddiy darsdagi yakuniy tekshiruvgacha kamida.
FINAL_CHECK_DELAY_DAYS = 3


def final_check_due_on(cleared_at: datetime) -> date:
    """Rejalashtiruvchi nishonni shu kundan boshlab ko'radi.

    Aniq shart (`cleared_at + 3 kun <= hozir`) rejalashtiruvchida tekshiriladi;
    bu sana faqat chegaralangan "muddati kelgan" so'rov uchun.
    """
    return (cleared_at + timedelta(days=FINAL_CHECK_DELAY_DAYS)).date()
