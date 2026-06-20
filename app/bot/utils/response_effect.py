import asyncio
from contextlib import suppress
from typing import Optional

from aiogram.types import Message


_STATE_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "qa": {
        "uz": ("Analiz qilyapman...", "Javob tayyorlayapman...", "Tekshiryapman...", "O'ylayapman..."),
        "ru": ("Анализирую...", "Готовлю ответ...", "Проверяю...", "Думаю..."),
        "tj": ("Таҳлил карда истодаам...", "Ҷавоб тайёр мекунам...", "Месанҷам...", "Фикр карда истодаам..."),
    },
    "course": {
        "uz": ("Darsni tahlil qilyapman...", "Javob tayyorlayapman...", "Tekshiryapman...", "O'ylayapman..."),
        "ru": ("Анализирую урок...", "Готовлю ответ...", "Проверяю...", "Думаю..."),
        "tj": ("Дарсро таҳлил карда истодаам...", "Ҷавоб тайёр мекунам...", "Месанҷам...", "Фикр карда истодаам..."),
    },
    "image": {
        "uz": ("Rasmni tahlil qilyapman...", "Matnni tekshiryapman...", "Javob tayyorlayapman...", "O'ylayapman..."),
        "ru": ("Анализирую фото...", "Проверяю текст...", "Готовлю ответ...", "Думаю..."),
        "tj": ("Суратро таҳлил карда истодаам...", "Матнро месанҷам...", "Ҷавоб тайёр мекунам...", "Фикр карда истодаам..."),
    },
    "voice": {
        "uz": ("Ovozni eshityapman...", "Matnga aylantiryapman...", "Ma'nosini tekshiryapman...", "Javob tayyorlayapman..."),
        "ru": ("Слушаю голос...", "Перевожу в текст...", "Проверяю смысл...", "Готовлю ответ..."),
        "tj": ("Овозро мешунавам...", "Ба матн мегузаронам...", "Маъниро месанҷам...", "Ҷавоб тайёр мекунам..."),
    },
    "translate": {
        "uz": ("Ovozni eshityapman...", "Matnga aylantiryapman...", "Tarjima qilyapman...", "Tekshiryapman..."),
        "ru": ("Слушаю голос...", "Перевожу в текст...", "Перевожу...", "Проверяю..."),
        "tj": ("Овозро мешунавам...", "Ба матн мегузаронам...", "Тарҷума мекунам...", "Месанҷам..."),
    },
}


def _select_states(mode: str, seed: int | None, lang: str = "uz") -> tuple[str, ...]:
    del seed
    mode_states = _STATE_POOLS.get(mode) or _STATE_POOLS["qa"]
    states = mode_states.get(lang) or mode_states.get("uz") or _STATE_POOLS["qa"]["uz"]
    if not states:
        return _STATE_POOLS["qa"]["uz"]
    return states


class ResponseEffect:
    def __init__(
        self,
        message: Message,
        step_delay: float = 1.6,
        states: tuple[str, ...] | None = None,
        delete_on_stop: bool = True,
        mode: str = "qa",
        seed: int | None = None,
        lang: str = "uz",
        typing_interval: float = 4.0,
    ):
        self.message = message
        self.step_delay = step_delay
        self.states = states or _select_states(mode, seed if seed is not None else message.message_id, lang)
        self.delete_on_stop = delete_on_stop
        self.temp_message = None
        self.typing_interval = typing_interval
        self._task: Optional[asyncio.Task] = None
        self._typing_task: Optional[asyncio.Task] = None
        self._stopped = False

    async def _send_typing(self) -> None:
        try:
            await self.message.bot.send_chat_action(chat_id=self.message.chat.id, action="typing")
        except Exception:
            pass

    async def _typing_runner(self) -> None:
        while not self._stopped:
            await asyncio.sleep(self.typing_interval)
            if not self._stopped:
                await self._send_typing()

    async def _runner(self):
        index = 1
        while not self._stopped:
            await asyncio.sleep(self.step_delay)
            if self._stopped:
                break

            try:
                await self.temp_message.edit_text(
                    self.states[index % len(self.states)]
                )
            except Exception:
                pass

            index += 1

    async def start(self):
        await self._send_typing()
        self.temp_message = await self.message.answer(self.states[0])
        self._task = asyncio.create_task(self._runner())
        self._typing_task = asyncio.create_task(self._typing_runner())

    async def set_text(self, text: str, **kwargs):
        if not self.temp_message:
            return
        try:
            await self.temp_message.edit_text(text, **kwargs)
        except Exception:
            pass

    async def stop(self):
        self._stopped = True

        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

        if self._typing_task:
            self._typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._typing_task

        if self.delete_on_stop and self.temp_message:
            try:
                await self.temp_message.delete()
            except Exception:
                pass
