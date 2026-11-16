"""Allowlisted capability manifest for the owner-triggered full analytics refresh.

One group is one section and one platform. The server refreshes a group only
when it is listed here, and the private-repository orchestrator must report the
same `MANIFEST_VERSION`, so neither side can expand the privileged endpoint.

Windows are listed only where the existing loader produces a genuine period
observation. Everything else is named with a reason instead of being refreshed:
- Platform and Report are current-state projections (`period_filter_applied`
  false / quality independent of period), so only the weekly snapshot exists.
- Experiments computes `all_time` as a rolling 30 days, not a lifetime value.
- Feedback has weekly and monthly category windows only.
Desktop (macOS/Windows) stays out under the development freeze.
"""

MANIFEST_VERSION = "hskai-full-refresh-v1"
PERIODS = ("weekly", "monthly", "all_time")
SECTION_ORDER = ("overview", "home", "course", "platform", "funnel", "money",
                 "sources", "report", "experiments", "feedback")
_MOBILE = ("overall", "android", "telegram", "iphone_pwa")


def _group(section, platform, periods, unsupported=None):
    unsupported = dict(unsupported or {})
    assert set(periods).isdisjoint(unsupported) and set(periods) | set(unsupported) == set(PERIODS)
    return {"section": section, "platform": platform, "periods": tuple(periods),
            "unsupported": unsupported}


_CURRENT_STATE = {"monthly": "period_independent", "all_time": "period_independent"}

GROUPS = (
    _group("overview", "overall", PERIODS),
    _group("home", "overall", PERIODS),
    *(_group("course", platform, PERIODS) for platform in _MOBILE),
    *(_group("platform", platform, ("weekly",), _CURRENT_STATE) for platform in _MOBILE),
    *(_group("funnel", platform, PERIODS) for platform in _MOBILE),
    *(_group("money", platform, PERIODS) for platform in _MOBILE),
    *(_group("sources", platform, PERIODS) for platform in _MOBILE),
    _group("report", "overall", ("weekly",), _CURRENT_STATE),
    _group("experiments", "overall", ("weekly", "monthly"),
           {"all_time": "rolling_30_days_not_lifetime"}),
    _group("feedback", "overall", ("weekly", "monthly"), {"all_time": "no_all_time_window"}),
)

EXCLUDED = (
    {"section": "overview", "platforms": ("android", "telegram", "iphone_pwa"),
     "reason": "platform_cards_not_overview_totals"},
    {"section": "home", "platforms": ("android", "telegram", "iphone_pwa"),
     "reason": "platform_cards_not_home_cohorts"},
    {"section": "report", "platforms": ("android", "telegram", "iphone_pwa"),
     "reason": "one_global_report"},
    {"section": "experiments", "platforms": ("android", "telegram", "iphone_pwa"),
     "reason": "overall_only_estimator"},
    {"section": "feedback", "platforms": ("android", "telegram", "iphone_pwa"),
     "reason": "all_sources_category_aggregate_only"},
    {"section": "*", "platforms": ("macos", "windows"), "reason": "desktop_development_freeze"},
)

_BY_KEY = {(group["section"], group["platform"]): group for group in GROUPS}


def group_for(section, platform):
    return _BY_KEY.get((section, platform))


def manifest():
    return {
        "manifest_version": MANIFEST_VERSION,
        "sections": list(SECTION_ORDER),
        "groups": [{"section": g["section"], "platform": g["platform"], "periods": list(g["periods"]),
                    "unsupported": dict(g["unsupported"])} for g in GROUPS],
        "excluded": [{"section": e["section"], "platforms": list(e["platforms"]),
                      "reason": e["reason"]} for e in EXCLUDED],
    }
