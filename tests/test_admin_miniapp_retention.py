from datetime import datetime, timedelta, timezone

import json

from app.services.admin_miniapp_service import (
    AdminMiniAppService,
    _activation_funnel,
    _cohort_retention,
    _d1_recovery_experiment,
    _lesson_attempt_durations,
    _miniapp_session_durations,
    _payment_attempt_funnel,
)


def test_retention_counts_only_the_exact_completed_day_window():
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    cohort_start = datetime(2026, 7, 1, 8, tzinfo=timezone.utc)
    recent_signup = now - timedelta(hours=30)
    created_by_user = {
        1: cohort_start,
        2: cohort_start,
        3: recent_signup,
    }
    opens_by_user = {
        1: [cohort_start + timedelta(hours=25)],
        2: [cohort_start + timedelta(days=7, hours=2)],
        3: [recent_signup + timedelta(hours=25)],
    }

    d1 = _cohort_retention(
        created_by_user=created_by_user,
        opens_by_user=opens_by_user,
        days=1,
        now=now,
    )
    d7 = _cohort_retention(
        created_by_user=created_by_user,
        opens_by_user=opens_by_user,
        days=7,
        now=now,
    )

    assert d1 == {"eligible": 2, "retained": 1, "rate": 50.0}
    assert d7 == {"eligible": 2, "retained": 1, "rate": 50.0}


def test_activation_uses_only_users_with_a_completed_measurement_window():
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    started = now - timedelta(days=2)
    rows = [
        ("onboarding_completed", 1, started, json.dumps({"activation_variant": "direct_start_v1"})),
        ("lesson_started", 1, started + timedelta(minutes=1)),
        ("section_completed", 1, started + timedelta(minutes=10)),
        ("lesson_completed", 1, started + timedelta(hours=2)),
        ("onboarding_completed", 2, started, json.dumps({"activation_variant": "direct_start_v1"})),
        ("lesson_started", 2, started + timedelta(minutes=3)),
        ("section_completed", 2, started + timedelta(minutes=16)),
        ("lesson_completed", 2, started + timedelta(hours=25)),
        ("onboarding_completed", 3, now - timedelta(minutes=1), json.dumps({"activation_variant": "direct_start_v1"})),
        ("lesson_started", 3, now),
    ]

    funnel = _activation_funnel(rows, now=now)

    assert funnel["onboarded"] == 3
    assert funnel["lesson_started_eligible"] == 2
    assert funnel["lesson_started_2m"] == 1
    assert funnel["lesson_started_rate"] == 50.0
    assert funnel["section_completed_eligible"] == 2
    assert funnel["section_completed_15m"] == 1
    assert funnel["lesson_completed_eligible"] == 2
    assert funnel["lesson_completed_24h"] == 1
    assert funnel["variants"]["direct_start_v1"]["lesson_started_rate"] == 50.0


def test_d1_recovery_uses_matured_assignment_windows_and_dedupes_completion():
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    assigned = now - timedelta(hours=72)

    def row(name, user, at, *, source="d1_recovery_v1", arm=None, lesson_id=10):
        payload = json.dumps({"arm": arm}) if arm else None
        return (name, user, source, "hsk1", lesson_id, 1, payload, at)

    rows = [
        row("d1_recovery_assigned", 1, assigned, arm="treatment"),
        row("d1_recovery_sent", 1, assigned + timedelta(seconds=1), arm="treatment"),
        row("miniapp_opened", 1, assigned + timedelta(hours=2)),
        row("lesson_completed", 1, assigned + timedelta(hours=5)),
        row("book_lesson_completed", 1, assigned + timedelta(hours=5)),
        row("d1_recovery_assigned", 2, assigned, arm="control"),
        row("miniapp_opened", 2, assigned + timedelta(hours=50), source="course_v3"),
        row("d1_recovery_assigned", 3, now - timedelta(hours=12), arm="treatment"),
        row("miniapp_opened", 3, now - timedelta(hours=2)),
    ]

    result = _d1_recovery_experiment(
        rows,
        [(1, assigned + timedelta(hours=10))],
        now=now,
    )

    treatment = result["arms"]["treatment"]
    control = result["arms"]["control"]
    assert treatment["assigned"] == 2
    assert treatment["matured"] == 1
    assert treatment["sent"] == 1
    assert treatment["opened_any_48h"] == 1
    assert treatment["opened_attributed_48h"] == 1
    assert treatment["lesson_completed_48h"] == 1
    assert treatment["blocked_48h"] == 1
    assert control["matured"] == 1
    assert control["opened_any_48h"] == 0
    assert result["uplift_pp"]["open"] == 100.0
    assert result["uplift_pp"]["completion"] == 100.0
    assert result["directional_only"] is True


def test_d1_report_marks_small_samples_as_early_and_empty_arms_as_collecting():
    arm = {
        "open_rate": 100.0,
        "opened_any_48h": 1,
        "matured": 1,
    }
    advanced = {
        "d1_recovery": {
            "collecting": False,
            "directional_only": True,
            "uplift_pp": {"open": 100.0},
            "arms": {"treatment": arm, "control": {**arm, "open_rate": 0.0}},
        }
    }

    early_text = AdminMiniAppService._advanced_report_text(advanced)
    assert "D1 recovery (erta signal)" in early_text
    assert "lift +100.0 pp" in early_text

    advanced["d1_recovery"] = {
        "collecting": True,
        "directional_only": True,
        "uplift_pp": {"open": 0.0},
        "arms": {"treatment": {}, "control": {}},
    }
    collecting_text = AdminMiniAppService._advanced_report_text(advanced)
    assert "D1 recovery: 48h natija yig'ilmoqda" in collecting_text
    assert "lift +0.0 pp" not in collecting_text


def test_lesson_time_pairs_completion_with_the_latest_matching_attempt():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)
    rows = [
        (1, "hsk1", 10, 1, "session-a", "lesson_started", started),
        (1, "hsk1", 10, 1, "session-b", "lesson_started", started + timedelta(hours=1)),
        (1, "hsk1", 10, 1, "session-b", "lesson_completed", started + timedelta(hours=1, minutes=13)),
        (1, "hsk1", 10, 1, "session-b", "book_lesson_completed", started + timedelta(hours=1, minutes=13)),
        (2, "hsk1", 10, 1, "session-c", "lesson_started", started),
        (2, "hsk1", 10, 1, None, "lesson_completed", started + timedelta(minutes=20)),
    ]

    durations = _lesson_attempt_durations(rows)

    assert sorted(durations) == [13 * 60, 20 * 60]


def test_lesson_time_does_not_pair_mismatched_nonlegacy_sessions():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)

    durations = _lesson_attempt_durations(
        [
            (1, "hsk1", 10, 1, "old-session", "lesson_started", started),
            (1, "hsk1", 10, 1, "new-session", "lesson_completed", started + timedelta(hours=2)),
        ]
    )

    assert durations == []


def test_session_time_splits_a_reused_session_id_after_long_idle():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)
    rows = [
        (1, "legacy-session", started),
        (1, "legacy-session", started + timedelta(minutes=5)),
        (1, "legacy-session", started + timedelta(hours=2)),
        (1, "legacy-session", started + timedelta(hours=2, minutes=10)),
        (2, "single-event", started),
    ]

    sessions, durations = _miniapp_session_durations(rows)

    assert sessions == 3
    assert sorted(durations) == [5 * 60, 10 * 60]


def test_payment_funnel_links_only_the_same_attempt_and_payment():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)
    rows = [
        ("checkout_opened", 1, None, json.dumps({"attempt_id": "sub-a"}), started),
        (
            "checkout_opened",
            1,
            None,
            json.dumps({"attempt_id": "sub-a", "stage": "payment_instructions_viewed"}),
            started + timedelta(minutes=1),
        ),
        (
            "checkout_opened",
            2,
            None,
            json.dumps({"attempt_id": "sub-missing", "stage": "payment_receipt_selected"}),
            started + timedelta(minutes=2),
        ),
        (
            "checkout_opened",
            1,
            None,
            json.dumps({"attempt_id": "sub-a", "stage": "payment_receipt_selected"}),
            started + timedelta(minutes=3),
        ),
        (
            "payment_screenshot_submitted",
            1,
            10,
            json.dumps({"attempt_id": "sub-a"}),
            started + timedelta(minutes=4),
        ),
        ("payment_approved", 1, 10, None, started + timedelta(minutes=5)),
        ("payment_screenshot_submitted", 3, 11, None, started + timedelta(minutes=6)),
    ]

    funnel = _payment_attempt_funnel(rows)

    assert [step["users"] for step in funnel["steps"]] == [1, 1, 1, 1, 1]
    assert funnel["attempts"] == 1
    assert funnel["collecting"] is False


def test_payment_funnel_waits_for_attempt_aware_events():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)
    funnel = _payment_attempt_funnel(
        [("checkout_opened", 1, None, json.dumps({"mode": "subscription"}), started)]
    )

    assert funnel["steps"] == []
    assert funnel["collecting"] is True
    assert funnel["abandon_step"] == "Ma'lumot yig'ilmoqda"


def test_payment_funnel_keeps_users_monotonic_when_a_client_stage_event_is_missing():
    started = datetime(2026, 7, 18, 8, tzinfo=timezone.utc)
    rows = [
        ("checkout_opened", 1, None, json.dumps({"attempt_id": "sub-a"}), started),
        (
            "payment_screenshot_submitted",
            1,
            10,
            json.dumps({"attempt_id": "sub-a"}),
            started + timedelta(minutes=4),
        ),
        ("payment_approved", 1, 10, None, started + timedelta(minutes=5)),
    ]

    funnel = _payment_attempt_funnel(rows)

    assert [step["users"] for step in funnel["steps"]] == [1, 1, 1, 1, 1]
