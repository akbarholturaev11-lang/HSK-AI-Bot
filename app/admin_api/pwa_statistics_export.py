"""Bounded aggregate files from the daily reader; no SQL or arbitrary fields."""
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
import re

from fastapi.responses import Response

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS
from app.admin_api.pwa_metrics import METRIC_DEFINITIONS

MAX_EXPORT_BYTES = 128 * 1024
MAX_CURRENCIES = 32
_SOURCES = {
    "overall": "AdminMiniAppService + pwa_metrics.overall_activity_metrics",
    "android": "AndroidAnalyticsService.snapshot",
    "macos": "DesktopAnalyticsService.snapshot.platforms",
    "windows": "DesktopAnalyticsService.snapshot.platforms",
}


def _date(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("Invalid export timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Missing export timezone")
    return parsed.astimezone(timezone.utc)


def statistics_export(data, query):
    """Allowlist every metric path. Unknown nested data is never serialized."""
    if data["platform"] != query.platform or data["period"] != query.period:
        raise ValueError("Foreign statistics snapshot")
    generated = _date(data["generated_at"])
    expires = _date(data["snapshot"]["expires_at"])
    if (expires - generated != timedelta(days=1) or expires <= datetime.now(timezone.utc)
            or data["snapshot"]["refresh_interval_seconds"] != 86400):
        raise ValueError("Invalid export snapshot age")
    days = {"weekly": 7, "monthly": 30, "all_time": None}[query.period]
    since = _date(data["since"]) if data["since"] is not None else None
    if since != (generated - timedelta(days=days) if days else None):
        raise ValueError("Invalid export range")
    available = data["available"]
    if type(available) is not bool:
        raise ValueError("Invalid export availability")
    result = {
        "schema_version": 1, "dataset": "hskai_statistics", "platform": query.platform,
        "period": query.period, "since": since.isoformat() if since else None,
        "generated_at": generated.isoformat(), "expires_at": expires.isoformat(),
        "refresh_interval_seconds": 86400, "timezone": "UTC",
        "platform_counts_overlap": True, "available": available, "reason": None,
        "source": _SOURCES.get(query.platform), "scope": {}, "metrics": [],
        "metric_definitions": METRIC_DEFINITIONS if query.platform == "overall" else {},
    }
    if not available:
        reason = {"telegram": "attribution_not_audited", "iphone_pwa": "not_instrumented"}.get(query.platform)
        if reason is None or data.get("reason") != reason or data.get("metrics") is not None:
            raise ValueError("Invalid unavailable snapshot")
        result["reason"] = reason
        return result
    if query.platform not in _SOURCES or data.get("source") != _SOURCES[query.platform]:
        raise ValueError("Invalid statistics source")
    metrics = data["metrics"]

    def add(path, unit, definition, date_basis, *, value=None, supplied=False, nullable=False):
        if not supplied:
            value = metrics
            for key in path.split("."):
                value = value[key]
        if not (nullable and value is None):
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 <= value <= 2**63 - 1 or (unit == "percent" and value > 100)):
                raise ValueError("Invalid aggregate value")
            if unit not in ("percent", "USD") and type(value) is not int:
                raise ValueError("Invalid aggregate count")
        result["metrics"].append({"metric": path, "value": value, "unit": unit,
                                  "definition": definition, "date_basis": date_basis})

    if query.platform == "overall":
        result["scope"] = {"users_total": "all_canonical_accounts", "new_accounts": query.period,
            "active_accounts_since": (since or generated - timedelta(days=30)).isoformat(),
            "payments": "reviewed_at_or_submitted_at"}
        add("users_total", "accounts", "All current canonical accounts, including admins.", "current users")
        add("new_accounts", "accounts", "Accounts registered in the selected period.", "users.created_at")
        add("active_accounts", "accounts", "Current accounts with last activity in range; all-time uses 30 days.", "users.last_active_at")
        for status in ("pending", "approved", "rejected"):
            add("payments_by_status." + status, "payments", "Payment records by current status; not unique buyers.", "coalesce(reviewed_at, submitted_at)")
        for name, unit, definition in (
            ("recorded_requests", "usage_rows", "Recorded usage rows, including unmatched historical owners."),
            ("tokens", "tokens", "Sum of stored total_tokens, without prompts or completions."),
            ("estimated_cost_usd", "USD", "Stored cost_usd sum; estimate, not a provider invoice."),
        ):
            add("ai_usage." + name, unit, definition, "ai_usage_events.created_at")
        for name in ("engaged_accounts", "started_accounts", "completed_accounts", "unmatched_events"):
            add("course_engagement." + name, "events" if name == "unmatched_events" else "accounts",
                "Event names and canonical deduplication are defined in metric_definitions.course_engagement; unmatched events are separate.",
                "course_miniapp_events.created_at")
        for name in ("registered_accounts", "converted_accounts", "percent"):
            add("registration_conversion." + name, "percent" if name == "percent" else "accounts",
                "Registration cohort approved Pro conversion to date; excludes unlock/manual/bonus/orphan payments. Percent = 100 * converted / registered, null for empty cohort.",
                "users.created_at; coalesce(payments.reviewed_at, payments.submitted_at)", nullable=name == "percent")
        amounts = metrics["approved_amounts_by_currency"]
        if not isinstance(amounts, list) or len(amounts) > MAX_CURRENCIES:
            raise ValueError("Too many export currencies")
        seen = set()
        for row in amounts:
            currency = row["currency"]
            if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency) or currency in seen:
                raise ValueError("Invalid export currency")
            seen.add(currency)
            add("approved_amounts_by_currency." + currency, currency,
                "Approved payment amount in the original currency; currencies are never summed together.",
                "coalesce(reviewed_at, submitted_at)", value=row["amount"], supplied=True)
    elif query.platform == "android":
        result["scope"] = {"registry": "current_linked_devices", "active": "rolling_1_7_30_days", "funnel": query.period}
        for name in ("installed_devices", "installed_users", "opened_devices", "opened_users", "never_opened_devices",
                     "unlinked_devices", "new_devices_in_period", "new_users_in_period"):
            add("registry." + name, "accounts" if "users" in name else "devices",
                "Device registry count; revoked devices counted only as unlinked. New counts use created_at, or all current links for all-time.", "desktop_devices current registry; created_at for new counts")
        for days in (1, 7, 30):
            for kind in ("devices", "users"):
                add(f"registry.online_{kind}_{days}d", "devices" if kind == "devices" else "accounts",
                    "Currently linked devices/accounts contacting the server in the rolling window; not foreground opens.", "desktop_devices.last_seen_at")
        for window in ("dau", "wau", "mau"):
            for suffix in ("", "_devices"):
                add("active." + window + suffix, "devices" if suffix else "analytics_identities",
                    "Recorded android_app_opened on currently linked devices in rolling 1/7/30 days; not selected-period totals.", "course_miniapp_events.created_at")
        for stage in ("apk_requested", "apk_sent", "session_linked", "first_open"):
            for kind in ("users", "events"):
                add(f"funnel.{stage}.{kind}", "analytics_identities" if kind == "users" else "events",
                    "Recorded Android stage in the selected period; users deduplicated by existing analytics identity rules.", "course_miniapp_events.created_at")
    else:
        result["scope"] = {"metrics": "rolling_30_days", "period_filter_applied": False}
        for name in ("download_requests_30d", "verified_first_open_30d", "active_users_30d"):
            add(name, "analytics_identities", "Distinct attributed desktop analytics identities over 30 days; selected period is not applied.", "course_miniapp_events.created_at")
    if len(result["metrics"]) > 96:
        raise ValueError("Too many export rows")
    return result


def render_statistics_export(data, query):
    result = statistics_export(data, query)
    if query.format == "json":
        raw = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        media_type = "application/json"
    elif query.format == "csv":
        metadata = {key: value for key, value in result.items() if key not in ("metrics", "metric_definitions")}
        metadata["scope"] = json.dumps(metadata["scope"], separators=(",", ":"))
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=[*metadata, "metric", "value", "unit", "definition", "date_basis"])
        writer.writeheader()
        # An unavailable platform has one explicit status row, never fake zero metrics.
        for row in result["metrics"] or [{}]:
            group = row.get("metric", "").split(".")[0]
            if group in METRIC_DEFINITIONS:
                row = {**row, "definition": row["definition"] + " " + json.dumps(METRIC_DEFINITIONS[group], separators=(",", ":"))}
            writer.writerow({**metadata, **row})
        raw = output.getvalue().encode("utf-8")
        media_type = "text/csv"
    else:
        raise ValueError("Invalid export format")
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError("Export too large")
    stamp = _date(result["generated_at"]).strftime("%Y%m%dT%H%M%SZ")
    filename = f"hskai-statistics-{query.platform}-{query.period}-{stamp}.{query.format}"
    return Response(raw, media_type=media_type, headers={**_PRIVATE_HEADERS,
        "Content-Disposition": f'attachment; filename="{filename}"'})
