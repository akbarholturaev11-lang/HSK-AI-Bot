"""Limitlar — kod emas, ma'lumot.

Bugun `FREE_FEATURE_LIMITS`, `COURSE_DAILY_FREE_LIMITS`, `TRIAL_LIMITS` va
`PAID_LIMITS` — Python konstantalari. Ya'ni "bepul dars 2 ta bo'lsin" degan
qarorni bajarish uchun deploy kerak.

Bu modul ularni `bot_settings` dagi bitta JSON qatoriga ko'chiradi. Shakl
ataylab `CourseAccessPolicyService` ga o'xshatilgan, chunki admin endpointi
o'shaning nusxasi bo'ladi.

Eng muhim qoida — **hech qachon exception tashlamaslik**. Buzilgan JSON,
noma'lum holat yoki noma'lum action faqat O'SHA bandda `defaults()` ga
qaytadi. Noto'g'ri admin tahriri na hamma qulfni ochadi, na funksiyani
o'ldiradi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.entitlements import actions as A
from app.services.entitlements.state import ENTITLEMENT_STATES, EntitlementState


ENTITLEMENT_LIMITS_KEY = "entitlement_limits_v1"
CONFIG_VERSION = 1

WINDOW_DAILY = "daily"
WINDOW_LIFETIME = "lifetime"
WINDOW_NONE = "none"
WINDOWS = frozenset({WINDOW_DAILY, WINDOW_LIFETIME, WINDOW_NONE})

#: Bitta limitning yuqori chegarasi. Bundan kattasi — deyarli aniq xato kiritish.
MAX_LIMIT = 10_000

#: Plan darajasidagi joker.
WILDCARD = "*"
INHERIT_PREFIX = "inherit:"


# --- default konfiguratsiya ------------------------------------------------
#
# FREE raqamlari kelishilgan reja bo'yicha (2 dars / 5 AI matn / 2 ovoz /
# 1 speaking). Mashq bo'limlari bugungi qiymatida (1/kun) qoldirildi, ya'ni
# bu default hech kimning limitini bugungidan TORAYTIRMAYDI.
#
# TRIAL raqamlari ataylab `null` emas: UI da "cheksiz" so'zi faqat `limit is
# null` bo'lganda chiqadi, ya'ni faqat PRO/TEMP uchun. Trial keng, lekin
# hisoblanadigan — AI xarajati nazorat ostida qoladi.

_DEFAULT_FREE = {
    A.LESSON_START: {"limit": 2, "window": WINDOW_DAILY},
    A.AI_TEXT: {"limit": 5, "window": WINDOW_DAILY},
    A.AI_PHOTO: {"limit": 5, "window": WINDOW_DAILY},
    A.AI_VOICE: {"limit": 2, "window": WINDOW_DAILY},
    A.SPEAKING_SESSION: {"limit": 1, "window": WINDOW_DAILY},
    "practice.*": {"limit": 1, "window": WINDOW_DAILY},
    A.PRACTICE_PLACEMENT: {"limit": 1, "window": WINDOW_LIFETIME},
    A.STUDY_QUIZ: {"limit": 1, "window": WINDOW_DAILY},
    A.STUDY_AUDIO: {"limit": 5, "window": WINDOW_DAILY},
    A.STUDY_FLASHCARD_TRANSLATE: {"limit": 20, "window": WINDOW_DAILY},
}

_DEFAULT_TRIAL = {
    A.LESSON_START: {"limit": 10, "window": WINDOW_DAILY},
    A.AI_TEXT: {"limit": 50, "window": WINDOW_DAILY},
    A.AI_PHOTO: {"limit": 20, "window": WINDOW_DAILY},
    A.AI_VOICE: {"limit": 15, "window": WINDOW_DAILY},
    A.SPEAKING_SESSION: {"limit": 3, "window": WINDOW_DAILY},
    "practice.*": {"limit": 10, "window": WINDOW_DAILY},
    A.STUDY_QUIZ: {"limit": 10, "window": WINDOW_DAILY},
    A.STUDY_AUDIO: {"limit": 50, "window": WINDOW_DAILY},
    A.STUDY_FLASHCARD_TRANSLATE: {"limit": 100, "window": WINDOW_DAILY},
}

_DEFAULT_UNLIMITED = {WILDCARD: {"limit": None, "window": WINDOW_NONE}}
_DEFAULT_BLOCKED = {WILDCARD: {"limit": 0, "window": WINDOW_NONE}}

DEFAULT_PLANS = {
    EntitlementState.FREE: _DEFAULT_FREE,
    EntitlementState.TRIAL_ACTIVE: _DEFAULT_TRIAL,
    EntitlementState.PRO_ACTIVE: _DEFAULT_UNLIMITED,
    EntitlementState.TEMP_ACCESS: _DEFAULT_UNLIMITED,
    EntitlementState.EXPIRED: {WILDCARD: f"{INHERIT_PREFIX}{EntitlementState.FREE}"},
    EntitlementState.BLOCKED: _DEFAULT_BLOCKED,
}

DEFAULT_TRIAL_SETTINGS = {
    "enabled": True,
    "days": 7,
    "ai_budget_usd": 1.5,
    "plan_type": "pro_trial_7_days",
    "min_account_age_hours": 0,
    "disabled_reason": "",
}

MAX_TRIAL_DAYS = 90
MAX_TRIAL_BUDGET_USD = 50.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class ActionLimit:
    """Bitta harakat uchun chegara. ``limit is None`` — cheksiz."""

    limit: int | None
    window: str

    @property
    def unlimited(self) -> bool:
        return self.limit is None

    def as_dict(self) -> dict:
        return {"limit": self.limit, "window": self.window}


UNLIMITED = ActionLimit(limit=None, window=WINDOW_NONE)
FORBIDDEN = ActionLimit(limit=0, window=WINDOW_NONE)


def _clean_rule(raw) -> ActionLimit | None:
    """Bitta bandni tozalaydi. Yaroqsiz bo'lsa None — chaqiruvchi defaultga tushadi."""
    if not isinstance(raw, dict):
        return None

    window = str(raw.get("window") or WINDOW_DAILY).strip().lower()
    if window not in WINDOWS:
        return None

    if "limit" not in raw:
        return None
    value = raw.get("limit")
    if value is None:
        return ActionLimit(limit=None, window=WINDOW_NONE)
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return None
    if limit < 0 or limit > MAX_LIMIT:
        return None
    # Cheksizni faqat `null` bildiradi; 0 — "umuman mumkin emas".
    return ActionLimit(limit=limit, window=window if limit else WINDOW_NONE)


def _clean_plan(raw) -> dict:
    """Bitta plan bo'limini tozalaydi; yaroqsiz bandlar tushib qoladi."""
    if not isinstance(raw, dict):
        return {}
    cleaned: dict = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name:
            continue
        known = name == WILDCARD or name.endswith(".*") or name in A.ACTION_SET
        if not known:
            continue
        if isinstance(value, str) and value.startswith(INHERIT_PREFIX):
            target = value[len(INHERIT_PREFIX) :].strip()
            if target in ENTITLEMENT_STATES:
                cleaned[name] = value
            continue
        rule = _clean_rule(value)
        if rule is not None:
            cleaned[name] = rule
    return cleaned


def _clean_trial(raw) -> dict:
    trial = dict(DEFAULT_TRIAL_SETTINGS)
    if not isinstance(raw, dict):
        return trial

    trial["enabled"] = bool(raw.get("enabled", trial["enabled"]))
    try:
        days = int(raw.get("days", trial["days"]))
        if 1 <= days <= MAX_TRIAL_DAYS:
            trial["days"] = days
    except (TypeError, ValueError):
        pass
    try:
        budget = float(raw.get("ai_budget_usd", trial["ai_budget_usd"]))
        if 0 < budget <= MAX_TRIAL_BUDGET_USD:
            trial["ai_budget_usd"] = budget
    except (TypeError, ValueError):
        pass
    try:
        hours = int(raw.get("min_account_age_hours", trial["min_account_age_hours"]))
        if 0 <= hours <= 24 * 365:
            trial["min_account_age_hours"] = hours
    except (TypeError, ValueError):
        pass
    reason = raw.get("disabled_reason")
    if isinstance(reason, str):
        trial["disabled_reason"] = reason.strip()[:200]
    return trial


@dataclass(frozen=True)
class LimitConfig:
    plans: dict = field(default_factory=dict)
    trial: dict = field(default_factory=lambda: dict(DEFAULT_TRIAL_SETTINGS))
    saved_at: datetime | None = None
    updated_by_telegram_id: int | None = None

    # --- o'qish -----------------------------------------------------------

    def _plan_rules(self, state: str, *, _seen: frozenset = frozenset()) -> dict:
        rules = self.plans.get(state)
        if rules is None:
            rules = _defaults_as_rules().get(state, {})
        return rules

    def limit_for(self, state: str, action: str) -> ActionLimit:
        """Shu holat va harakat uchun chegara. HECH QACHON exception tashlamaydi."""
        if state not in ENTITLEMENT_STATES:
            state = EntitlementState.FREE
        action = A.normalize(action)

        seen: set[str] = set()
        while state not in seen:
            seen.add(state)
            rules = self._plan_rules(state)
            # Aniqdan umumiyga: aynan action -> prefiks jokeri -> plan jokeri.
            for key in (action, f"{action.split('.', 1)[0]}.*", WILDCARD):
                found = rules.get(key)
                if found is None:
                    continue
                if isinstance(found, str) and found.startswith(INHERIT_PREFIX):
                    nxt = found[len(INHERIT_PREFIX) :].strip()
                    if nxt in ENTITLEMENT_STATES and nxt not in seen:
                        state = nxt
                        break
                    return _default_limit(EntitlementState.FREE, action)
                return found
            else:
                return _default_limit(state, action)
        return _default_limit(EntitlementState.FREE, action)

    # --- yozish/ko'rsatish -------------------------------------------------

    def public_payload(self) -> dict:
        plans = {}
        for state in ENTITLEMENT_STATES:
            rules = self._plan_rules(state)
            plans[state] = {
                key: (value if isinstance(value, str) else value.as_dict())
                for key, value in rules.items()
            }
        return {
            "version": CONFIG_VERSION,
            "plans": plans,
            "trial": dict(self.trial),
            "saved_at": _iso(self.saved_at),
            "updated_by_telegram_id": self.updated_by_telegram_id,
        }

    def stored_payload(self) -> dict:
        return self.public_payload()


_DEFAULT_RULE_CACHE: dict | None = None


def _defaults_as_rules() -> dict:
    """Defaultlarni bir marta `ActionLimit` ga aylantiradi."""
    global _DEFAULT_RULE_CACHE
    if _DEFAULT_RULE_CACHE is None:
        _DEFAULT_RULE_CACHE = {
            state: _clean_plan(rules) for state, rules in DEFAULT_PLANS.items()
        }
    return _DEFAULT_RULE_CACHE


def _default_limit(state: str, action: str) -> ActionLimit:
    """Default konfiguratsiyadagi chegara — oxirgi tayanch."""
    rules = _defaults_as_rules().get(state, {})
    for key in (action, f"{action.split('.', 1)[0]}.*", WILDCARD):
        found = rules.get(key)
        if isinstance(found, ActionLimit):
            return found
        if isinstance(found, str) and found.startswith(INHERIT_PREFIX):
            target = found[len(INHERIT_PREFIX) :].strip()
            if target != state:
                return _default_limit(target, action)
    if state == EntitlementState.BLOCKED:
        return FORBIDDEN
    if state in (EntitlementState.PRO_ACTIVE, EntitlementState.TEMP_ACCESS):
        return UNLIMITED
    # Noma'lum bandda eng ehtiyotkor tanlov: bepul darajadagi chegara.
    free_rules = _defaults_as_rules()[EntitlementState.FREE]
    fallback = free_rules.get(action) or free_rules.get("practice.*")
    return fallback if isinstance(fallback, ActionLimit) else ActionLimit(1, WINDOW_DAILY)


def default_config() -> LimitConfig:
    return LimitConfig(
        plans=dict(_defaults_as_rules()),
        trial=dict(DEFAULT_TRIAL_SETTINGS),
    )


def config_from_payload(payload) -> LimitConfig:
    """Saqlangan JSON dan konfiguratsiya. Yaroqsiz qismlar defaultga tushadi."""
    if not isinstance(payload, dict):
        return default_config()

    defaults = _defaults_as_rules()
    raw_plans = payload.get("plans")
    plans: dict = {}
    for state in ENTITLEMENT_STATES:
        cleaned = _clean_plan((raw_plans or {}).get(state)) if isinstance(raw_plans, dict) else {}
        plans[state] = cleaned or dict(defaults.get(state, {}))

    try:
        updated_by = int(payload.get("updated_by_telegram_id") or 0) or None
    except (TypeError, ValueError):
        updated_by = None

    return LimitConfig(
        plans=plans,
        trial=_clean_trial(payload.get("trial")),
        saved_at=_parse_dt(payload.get("saved_at")),
        updated_by_telegram_id=updated_by,
    )


class LimitConfigService:
    def __init__(self, session):
        self.session = session
        self.repo = BotSettingRepository(session)

    async def get_config(self) -> LimitConfig:
        raw = await self.repo.get(ENTITLEMENT_LIMITS_KEY)
        if not raw:
            return default_config()
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return default_config()
        return config_from_payload(payload)

    async def get_payload(self) -> dict:
        return (await self.get_config()).public_payload()

    async def save_config(
        self,
        payload: dict,
        *,
        updated_by_telegram_id: int | None = None,
    ) -> LimitConfig:
        """Adminning tahririni saqlaydi.

        `get_config` yaroqsiz bandni jimgina defaultga aylantiradi, bu yerda esa
        ATAYLAB `ValueError` tashlanadi: admin nima yozganini bilishi kerak.
        """
        if not isinstance(payload, dict):
            raise ValueError("invalid_limits_config")

        raw_plans = payload.get("plans")
        if not isinstance(raw_plans, dict) or not raw_plans:
            raise ValueError("invalid_limits_config")

        plans: dict = {}
        for state, rules in raw_plans.items():
            if state not in ENTITLEMENT_STATES:
                raise ValueError("invalid_limits_config")
            if not isinstance(rules, dict) or not rules:
                raise ValueError("invalid_limits_config")
            cleaned = _clean_plan(rules)
            if len(cleaned) != len(rules):
                raise ValueError("invalid_limits_config")
            plans[state] = cleaned

        free_rules = plans.get(EntitlementState.FREE)
        if free_rules is None:
            raise ValueError("invalid_limits_config")
        # Bepul darajani butunlay cheksiz qilib qo'yish — daromad hodisasi,
        # va deyarli har doim tasodifiy. Buni maxsus rad etamiz.
        if all(
            isinstance(rule, ActionLimit) and rule.unlimited for rule in free_rules.values()
        ):
            raise ValueError("invalid_limits_config")

        defaults = _defaults_as_rules()
        for state in ENTITLEMENT_STATES:
            plans.setdefault(state, dict(defaults.get(state, {})))

        try:
            updated_by = int(updated_by_telegram_id or 0) or None
        except (TypeError, ValueError):
            updated_by = None

        config = LimitConfig(
            plans=plans,
            trial=_clean_trial(payload.get("trial")),
            saved_at=_utcnow(),
            updated_by_telegram_id=updated_by,
        )
        await self.repo.set(
            ENTITLEMENT_LIMITS_KEY,
            json.dumps(
                config.stored_payload(), ensure_ascii=False, separators=(",", ":")
            ),
        )
        return config
