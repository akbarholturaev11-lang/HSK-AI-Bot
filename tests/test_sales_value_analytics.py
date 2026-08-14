import json
from datetime import datetime, timedelta, timezone

from app.services.admin_miniapp_service import (
    AdminMiniAppService,
    _newcombe_difference_ci,
    _sales_value_card,
    _sales_value_experiment,
    _wilson_interval,
)


NOW = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def course_event(
    name,
    user,
    at,
    *,
    arm=None,
    mode="ab",
    candidate_pct=50,
    source=None,
    payload=None,
    level="hsk1",
    lesson_order=1,
):
    data = dict(payload or {})
    if name == "sales_offer_assigned":
        data.update(
            {
                "arm": arm,
                "assigned_mode": mode,
                "treatment_percent": candidate_pct,
            }
        )
        source = source or "sales_value_v1"
    return (
        name,
        user,
        source or "course_v3",
        level,
        10,
        lesson_order,
        json.dumps(data),
        at,
    )


def funnel_event(name, user, at, *, attempt_id="attempt-1", payment_id=None, stage=None):
    payload = {"attempt_id": attempt_id}
    if stage:
        payload["stage"] = stage
    return (name, user, payment_id, json.dumps(payload), at)


def payment_row(
    payment_id,
    user,
    status,
    *,
    reviewed_at=None,
    submitted_at=None,
    amount=100,
    currency="TJS",
):
    return (
        payment_id,
        user,
        status,
        amount,
        currency,
        None,
        reviewed_at,
        submitted_at or reviewed_at,
    )


def balanced_assignments(*, assigned_at, per_arm=200):
    rows = []
    for user in range(1, per_arm + 1):
        rows.append(course_event("sales_offer_assigned", user, assigned_at, arm="treatment"))
    for user in range(10_001, 10_001 + per_arm):
        rows.append(course_event("sales_offer_assigned", user, assigned_at, arm="control"))
    return rows


def test_sales_value_uses_only_matured_users_and_reviewed_at_approval_window():
    assigned = NOW - timedelta(days=10)
    recent = NOW - timedelta(days=3)
    course_rows = [
        course_event("sales_offer_assigned", 1, assigned, arm="treatment"),
        course_event("sales_offer_assigned", 2, assigned, arm="control"),
        course_event("sales_offer_assigned", 3, recent, arm="treatment"),
        course_event(
            "sales_bridge_seen",
            1,
            assigned + timedelta(minutes=1),
            payload={"arm": "control"},  # Client payload cannot change assignment.
        ),
        course_event("sales_bridge_cta", 1, assigned + timedelta(minutes=2)),
        course_event("sales_offer_seen", 1, assigned + timedelta(minutes=3)),
        course_event("paywall_seen", 1, assigned + timedelta(minutes=4)),
        course_event("foundation_completed", 1, assigned + timedelta(minutes=10)),
        course_event(
            "section_completed",
            1,
            assigned + timedelta(minutes=30),
            payload={"section_no": 3},
            level="hsk1",
            lesson_order=1,
        ),
        course_event("section_completed", 1, assigned + timedelta(hours=25)),
    ]
    funnel_rows = [
        funnel_event("checkout_opened", 1, assigned + timedelta(days=1)),
        funnel_event(
            "payment_screenshot_submitted",
            1,
            assigned + timedelta(days=1, minutes=2),
            payment_id=10,
        ),
    ]
    payment_rows = [
        payment_row(10, 1, "approved", reviewed_at=assigned + timedelta(days=2)),
        # The seven-day deadline is a half-open boundary and is excluded.
        payment_row(11, 2, "approved", reviewed_at=assigned + timedelta(days=7)),
        # An immature assignment cannot enter the denominator or outcomes.
        payment_row(12, 3, "approved", reviewed_at=recent + timedelta(days=1)),
        # submitted_at is deliberately not used as an approval-time fallback.
        payment_row(
            13,
            2,
            "approved",
            reviewed_at=None,
            submitted_at=assigned + timedelta(days=2),
        ),
        # A historical approval before assignment is not attributed.
        payment_row(14, 1, "approved", reviewed_at=assigned - timedelta(hours=1)),
        payment_row(15, 2, "rejected", reviewed_at=assigned + timedelta(days=2)),
        payment_row(16, 2, "pending", submitted_at=assigned + timedelta(days=3)),
    ]

    result = _sales_value_experiment(course_rows, funnel_rows, payment_rows, now=NOW)

    treatment = result["arms"]["treatment"]
    control = result["arms"]["control"]
    assert treatment["assigned"] == 2
    assert treatment["matured"] == 1
    assert control["matured"] == 1
    assert treatment["approved_users"] == 1
    assert treatment["approved_payments"] == 1
    assert treatment["approved_after_submit"] == 1
    assert treatment["revenue_by_currency"] == {"TJS": 100}
    assert treatment["foundation_completion_rate"] == 100.0
    assert treatment["first_checkpoint_completion_rate"] == 100.0
    assert treatment["d1_meaningful_return_rate"] == 100.0
    assert control["approved_users"] == 0
    assert control["rejected_users"] == 1
    assert control["pending_users"] == 1


def test_sales_value_uses_first_server_assignment_and_excludes_non_ab_modes():
    assigned = NOW - timedelta(days=10)
    rows = [
        course_event(
            "sales_offer_assigned",
            1,
            assigned,
            arm="treatment",
            payload={"mode": "treatment", "candidate_pct": 0},
        ),
        # A duplicate cannot move the same user to another arm.
        course_event("sales_offer_assigned", 1, assigned + timedelta(hours=1), arm="control"),
        course_event("sales_offer_seen", 1, assigned + timedelta(hours=2), payload={"arm": "control"}),
        course_event("sales_offer_assigned", 2, assigned, arm="treatment", mode="shadow"),
        course_event("sales_offer_assigned", 3, assigned, arm="treatment", mode="treatment"),
        course_event("sales_offer_assigned", 4, assigned, arm="invalid"),
    ]

    result = _sales_value_experiment(rows, [], [], now=NOW)

    assert result["assigned"] == 1
    assert result["excluded_assignments"] == 3
    assert result["arms"]["treatment"]["matured"] == 1
    assert result["arms"]["treatment"]["offer_seen"] == 1
    assert result["arms"]["control"]["assigned"] == 0
    assert result["status"] == "collecting"


def test_sales_value_declares_winner_only_after_thresholds_and_positive_ci():
    assigned = NOW - timedelta(days=20)
    course_rows = balanced_assignments(assigned_at=assigned)
    payment_rows = [
        payment_row(index, index, "approved", reviewed_at=assigned + timedelta(days=1))
        for index in range(1, 41)
    ] + [
        payment_row(1_000 + offset, 10_000 + offset, "approved", reviewed_at=assigned + timedelta(days=1))
        for offset in range(1, 11)
    ]

    result = _sales_value_experiment(course_rows, [], payment_rows, now=NOW)

    assert result["decision_ready"] is True
    assert result["arms"]["treatment"]["approval_rate"] == 20.0
    assert result["arms"]["control"]["approval_rate"] == 5.0
    assert result["uplift_pp"] == 15.0
    assert result["relative_lift_pct"] == 300.0
    assert result["ci_95_pp"]["low_pp"] > 0
    assert result["srm"]["mismatch"] is False
    assert result["status"] == "winner"
    assert result["decision"] == "promote"


def test_sales_value_blocks_winner_when_learning_guardrail_drops_over_five_pp():
    assigned = NOW - timedelta(days=20)
    course_rows = balanced_assignments(assigned_at=assigned)
    course_rows.extend(
        event
        for user in range(10_001, 10_041)
        for event in (
            course_event("foundation_completed", user, assigned + timedelta(hours=1)),
            course_event(
                "lesson_completed",
                user,
                assigned + timedelta(hours=2),
                level="hsk1",
                lesson_order=3,
            ),
            course_event("section_completed", user, assigned + timedelta(hours=25)),
        )
    )
    payment_rows = [
        payment_row(index, index, "approved", reviewed_at=assigned + timedelta(days=1))
        for index in range(1, 41)
    ] + [
        payment_row(1_000 + offset, 10_000 + offset, "approved", reviewed_at=assigned + timedelta(days=1))
        for offset in range(1, 11)
    ]

    error_rows = [
        (user, assigned + timedelta(hours=3))
        for user in range(1, 41)
    ]
    result = _sales_value_experiment(
        course_rows,
        [],
        payment_rows,
        now=NOW,
        error_rows=error_rows,
    )

    assert result["decision_ready"] is True
    assert result["guardrails"]["foundation"] == {"delta_pp": -20.0, "pass": False}
    assert result["guardrails"]["first_checkpoint"] == {"delta_pp": -20.0, "pass": False}
    assert result["guardrails"]["learning"] == {"delta_pp": -20.0, "pass": False}
    assert result["guardrails"]["frontend_error"] == {
        "delta_pp": 20.0,
        "pass": False,
        "available": True,
    }
    assert result["guardrails"]["pass"] is False
    assert result["status"] == "guardrail_failed"
    assert result["decision"] == "rollback"


def test_sales_value_flags_sample_ratio_mismatch():
    assigned = NOW - timedelta(days=20)
    rows = [
        course_event("sales_offer_assigned", user, assigned, arm="treatment")
        for user in range(1, 191)
    ] + [
        course_event("sales_offer_assigned", 10_000 + user, assigned, arm="control")
        for user in range(1, 11)
    ]

    result = _sales_value_experiment(rows, [], [], now=NOW)

    assert result["srm"]["checked"] is True
    assert result["srm"]["mismatch"] is True
    assert result["srm"]["p_value"] < 0.01
    assert result["status"] == "srm_warning"
    assert result["decision"] == "investigate"


def test_sales_value_srm_uses_assignment_time_ninety_ten_split():
    assigned = NOW - timedelta(days=20)
    rows = [
        course_event(
            "sales_offer_assigned",
            user,
            assigned,
            arm="treatment",
            candidate_pct=90,
        )
        for user in range(1, 91)
    ] + [
        course_event(
            "sales_offer_assigned",
            10_000 + user,
            assigned,
            arm="control",
            candidate_pct=90,
        )
        for user in range(1, 11)
    ]

    result = _sales_value_experiment(rows, [], [], now=NOW)

    assert result["srm"]["expected"] == {"treatment": 90.0, "control": 10.0}
    assert result["srm"]["mismatch"] is False
    assert result["status"] == "early_signal"


def test_sales_value_marks_42_day_no_lift_as_inconclusive_and_keeps_control():
    assigned = NOW - timedelta(days=50)
    course_rows = balanced_assignments(assigned_at=assigned)
    payment_rows = [
        payment_row(index, index, "approved", reviewed_at=assigned + timedelta(days=1))
        for index in range(1, 21)
    ] + [
        payment_row(1_000 + offset, 10_000 + offset, "approved", reviewed_at=assigned + timedelta(days=1))
        for offset in range(1, 21)
    ]

    result = _sales_value_experiment(course_rows, [], payment_rows, now=NOW)

    assert result["decision_ready"] is True
    assert result["uplift_pp"] == 0.0
    assert result["status"] == "inconclusive"
    assert result["decision"] == "keep_control"


def test_sales_value_wilson_ci_and_admin_card_are_stable_at_zero_denominator():
    assert _wilson_interval(0, 0) == (None, None)
    assert _newcombe_difference_ci(1, 10, 0, 0) == {"low_pp": None, "high_pp": None}

    result = _sales_value_experiment([], [], [], now=NOW)
    card = _sales_value_card(result)
    text = AdminMiniAppService._advanced_report_text({"sales_value": result})

    assert card["label"] == "Sales A/B · 7d approved"
    assert card["value"] == "Yig'ilmoqda"
    assert "CI yig'ilmoqda" in card["note"]
    assert "Sales A/B 7d (yig'ilmoqda)" in text
    assert "frontend error mavjud emas" in text
