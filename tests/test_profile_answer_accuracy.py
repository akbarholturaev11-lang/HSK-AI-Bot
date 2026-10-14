"""Do not show invented 100% accuracy or count duplicate lesson completion events."""
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.course_answer_accuracy_service import accuracy_summary


UTC = timezone.utc

def event(name, lesson, payload, hour=12, day=14):
    return (name, lesson, json.dumps(payload), datetime(2026, 10, day, hour, 0, tzinfo=UTC))


def test_empty_is_unknown_not_perfect():
    result = accuracy_summary([], [], now=datetime(2026, 10, 14, 18, tzinfo=UTC))
    assert result["overall"]["percent"] is None
    assert result["today"]["percent"] is None
    assert result["overall"]["total"] == 0


def test_weighted_answers_and_daily_timezone_boundary():
    events = [
        event("section_completed", 10, {"section_key": "a", "correct": 9, "total": 10}, hour=15, day=13),
        event("training_completed", None, {"score": 3, "total": 10}, hour=20, day=13),
    ]
    result = accuracy_summary(events, [], timezone_offset_minutes=480, now=datetime(2026, 10, 14, 12, tzinfo=UTC))
    assert result["overall"] == {"percent": 60, "correct": 12, "total": 20, "wrong": 8}
    assert result["today"] == {"percent": 30, "correct": 3, "total": 10, "wrong": 7}


def test_new_attempt_not_counted_twice_when_success_event_also_exists():
    rows = [
        event("section_attempt_scored", 10, {"section_key": "a", "correct": 6, "total": 10}),
        event("section_completed", 10, {"section_key": "a", "correct": 6, "total": 10}),
        event("section_attempt_scored", 10, {"section_key": "a", "correct": 9, "total": 10}, hour=14),
    ]
    r = accuracy_summary(rows, [], now=datetime(2026, 10, 14, 15, tzinfo=UTC))
    assert r["overall"]["correct"] == 15
    assert r["overall"]["total"] == 20
    assert r["overall"]["percent"] == 75


def test_failed_submission_counts_and_legacy_quiz():
    rows = [event("section_attempt_scored", 22, {"section_key": "b", "correct": 1, "total": 10})]
    quiz = [(json.dumps({"source": "miniapp_server_graded", "score": 7, "total": 10}),
             datetime(2026, 10, 14, 9, tzinfo=UTC))]
    r = accuracy_summary(rows, quiz, now=datetime(2026, 10, 14, 15, tzinfo=UTC))
    assert r["today"]["percent"] == 40
    assert r["overall"]["wrong"] == 12


def test_invalid_or_client_only_events_never_inflate_score():
    rows = [
        event("test_completed", None, {"score": 100}),  # percentage-only client score
        event("training_completed", None, {"score": 11, "total": 10}),
        event("section_completed", 11, {"correct": 0, "total": 0}),
        event("mistake_review_answered", None, {"answer_type": "tokens", "correct": False}),
        event("mistake_review_answered", None, {"selected_index": 0, "correct_index": 0}),
    ]
    r = accuracy_summary(rows, [], now=datetime(2026, 10, 14, 15, tzinfo=UTC))
    assert r["overall"] == {"percent": 50, "correct": 1, "total": 2, "wrong": 1}


def test_cross_platform_contract_and_status_cta():
    web = Path("app/static/course-v3.html").read_text(encoding="utf-8")
    android = Path("android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt").read_text(encoding="utf-8")
    dto = Path("android/app/src/main/java/com/pomp/hskai/data/api/AndroidFeatureDto.kt").read_text(encoding="utf-8")
    service = Path("app/services/study_miniapp_service.py").read_text(encoding="utf-8")
    assert 'loadProfileDetail();' in web
    assert 'profileAccuracyHtml()' in web
    assert 'class="pname"' not in web.split("function renderProfile(){",1)[1].split("/* ---------- sales_value_v1",1)[0]
    assert 'profile_after_streak' in web
    assert 'ProfileAccuracyRings(state.profile?.stats?.answerAccuracy)' in android
    assert "ProfileProCta" in android
    assert "showProCrown" not in android
    assert 'SerialName("answer_accuracy")' in dto
    assert '"answer_accuracy": accuracy' in service
