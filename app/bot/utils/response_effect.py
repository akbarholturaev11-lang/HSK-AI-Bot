import asyncio
from contextlib import suppress
from typing import Optional

from aiogram.types import Message


_STATE_POOLS: dict[str, tuple[tuple[str, ...], ...]] = {
    "qa": (
        ("🤔", "🧠", "✍️", "🔎", "✨"),
        ("💡", "📖", "🧩", "✍️", "✅"),
        ("🔍", "🧠", "📚", "✍️", "💫"),
        ("📝", "🔎", "💡", "🧠", "✍️"),
    ),
    "course": (
        ("📚", "🔤", "🧩", "✍️", "🎯"),
        ("📘", "💬", "🧠", "📝", "✅"),
        ("🧑‍🏫", "📖", "🔎", "✍️", "✨"),
    ),
    "image": (
        ("📷", "🔎", "🧠", "✍️", "✨"),
        ("🖼️", "🔍", "📖", "💡", "✍️"),
        ("📸", "🔤", "🧩", "🧠", "✅"),
    ),
}


def _select_states(mode: str, seed: int | None) -> tuple[str, ...]:
    pools = _STATE_POOLS.get(mode) or _STATE_POOLS["qa"]
    index = abs(seed or 0) % len(pools)
    return pools[index]


class ResponseEffect:
    def __init__(
        self,
        message: Message,
        step_delay: float = 1.6,
        states: tuple[str, ...] | None = None,
        delete_on_stop: bool = True,
        mode: str = "qa",
        seed: int | None = None,
    ):
        self.message = message
        self.step_delay = step_delay
        self.states = states or _select_states(mode, seed if seed is not None else message.message_id)
        self.delete_on_stop = delete_on_stop
        self.temp_message = None
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

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
        self.temp_message = await self.message.answer(self.states[0])
        self._task = asyncio.create_task(self._runner())

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

        if self.delete_on_stop and self.temp_message:
            try:
                await self.temp_message.delete()
            except Exception:
                pass
