import unittest
from unittest.mock import AsyncMock, MagicMock

from app.services import ai_provider
from app.services.ai_provider import AIProviderChain, GEMINI_MODEL_OPTIONS


def _mock_response():
    resp = MagicMock()
    message = MagicMock()
    message.content = "javob"
    choice = MagicMock()
    choice.message = message
    resp.choices = [choice]
    resp.usage = MagicMock(prompt_tokens=5, completion_tokens=7, total_tokens=12)
    return resp


def _build_chain(*, gemini=False, openai=False, gemini_side_effect=None, openai_side_effect=None):
    """__init__ ni chetlab o'tib, mijozlarni mock bilan quramiz (real API kalit kerak emas)."""
    chain = AIProviderChain.__new__(AIProviderChain)
    chain._gemini_native = None
    if gemini:
        chain._gemini_compat = MagicMock()
        chain._gemini_compat.chat.completions.create = AsyncMock(
            return_value=_mock_response(), side_effect=gemini_side_effect
        )
    else:
        chain._gemini_compat = None
    if openai:
        chain._openai = MagicMock()
        chain._openai.chat.completions.create = AsyncMock(
            return_value=_mock_response(), side_effect=openai_side_effect
        )
    else:
        chain._openai = None
    return chain


class AIProviderChainTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_primary_used_and_params_normalized(self):
        chain = _build_chain(gemini=True, openai=True)
        _, model_used = await chain.chat_completion(
            openai_model="gpt-4o-mini",
            messages=[{"role": "user", "content": "salom"}],
            max_completion_tokens=100,
            temperature=0.5,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            response_format={"type": "json_object"},
            gemini_model="gemini-2.5-flash",
        )
        self.assertEqual(model_used, "gemini-2.5-flash")
        chain._openai.chat.completions.create.assert_not_awaited()
        req = chain._gemini_compat.chat.completions.create.call_args.kwargs
        # Gemini OpenAI-mos endpointi max_tokens ishlatadi, penalties uzatilmaydi
        self.assertEqual(req["model"], "gemini-2.5-flash")
        self.assertEqual(req["max_tokens"], 100)
        self.assertNotIn("max_completion_tokens", req)
        self.assertNotIn("frequency_penalty", req)
        self.assertNotIn("presence_penalty", req)
        self.assertEqual(req["temperature"], 0.5)
        self.assertEqual(req["response_format"], {"type": "json_object"})

    async def test_openai_fallback_when_gemini_fails(self):
        chain = _build_chain(gemini=True, openai=True, gemini_side_effect=RuntimeError("gemini down"))
        _, model_used = await chain.chat_completion(
            openai_model="o4-mini",
            messages=[{"role": "user", "content": "salom"}],
            max_completion_tokens=200,
            gemini_model="gemini-2.5-pro",
        )
        self.assertEqual(model_used, "o4-mini")
        chain._gemini_compat.chat.completions.create.assert_awaited_once()
        chain._openai.chat.completions.create.assert_awaited_once()
        req = chain._openai.chat.completions.create.call_args.kwargs
        # OpenAI asl xatti-harakati: max_completion_tokens, max_tokens EMAS
        self.assertEqual(req["model"], "o4-mini")
        self.assertEqual(req["max_completion_tokens"], 200)
        self.assertNotIn("max_tokens", req)

    async def test_only_openai_when_no_gemini_key(self):
        chain = _build_chain(gemini=False, openai=True)
        _, model_used = await chain.chat_completion(
            openai_model="gpt-4o-mini",
            messages=[{"role": "user", "content": "salom"}],
        )
        self.assertEqual(model_used, "gpt-4o-mini")
        chain._openai.chat.completions.create.assert_awaited_once()

    async def test_raises_when_no_provider_configured(self):
        chain = _build_chain(gemini=False, openai=False)
        with self.assertRaises(RuntimeError):
            await chain.chat_completion(openai_model="o4-mini", messages=[])

    async def test_gemini_error_propagates_when_no_openai_fallback(self):
        chain = _build_chain(gemini=True, openai=False, gemini_side_effect=RuntimeError("boom"))
        with self.assertRaises(RuntimeError):
            await chain.chat_completion(
                openai_model="o4-mini", messages=[], gemini_model="gemini-2.5-flash"
            )


class ActiveGeminiModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_returns_value_without_db(self):
        ai_provider.set_active_gemini_model_cache("gemini-2.5-pro")
        self.assertEqual(await ai_provider.get_active_gemini_model(), "gemini-2.5-pro")

    def test_model_options_are_the_three_expected(self):
        self.assertEqual(
            GEMINI_MODEL_OPTIONS,
            ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
        )


if __name__ == "__main__":
    unittest.main()
