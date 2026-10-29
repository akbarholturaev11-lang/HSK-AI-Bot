"""Export existing shared semantic fixtures as complete Android test envelopes.

No runtime defaults, settings, network or database. QA calibration stays in
the explicit fixture cases; Android consumes results, never reimplements it.
"""
import argparse
from datetime import datetime, time, timedelta
import json
from pathlib import Path

from app.services.smart_reminder_policy import HabitCalibration, PolicyContext, VerifiedStudy
from app.services.smart_widget_context import WidgetContextRequest, project_widget

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("android/app/src/test/resources/smart_widget_context_v1.json")
EPOCH = "00000000-0000-4000-8000-000000000001"


def output(root=ROOT):
    source = json.loads((root / "tests/fixtures/smart_widget_context_v1.json").read_text())
    rows = []
    for case in source["cases"]:
        values = source["base"] | case["changes"]
        values["observed_at"] = datetime.fromisoformat(values["observed_at"])
        for key in ("saved_time", "manual_time", "quiet_start", "quiet_end"):
            if values.get(key) is not None:
                values[key] = time.fromisoformat(values[key])
        if values.get("pause_until"):
            values["pause_until"] = datetime.fromisoformat(values["pause_until"])
        values["permitted_channels"] = tuple(values["permitted_channels"])
        values["studies"] = tuple(VerifiedStudy(**(s | {"accepted_at": datetime.fromisoformat(s["accepted_at"])}))
                                  for s in values.get("studies", ()))
        context = PolicyContext(**values)
        calibration = HabitCalibration("shared-fixture-only", 3) if case["qa_habit_calibration"] else None
        envelope = project_widget(context, request=WidgetContextRequest(version=1, epoch=EPOCH),
            binding="a" * 64, valid_until=context.observed_at + timedelta(hours=1), calibration=calibration)
        rows.append({"name": case["name"], "context": envelope.model_dump(mode="json")})
    return json.dumps({"version": 1, "source": "tests/fixtures/smart_widget_context_v1.json", "cases": rows},
                      ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target, data = ROOT / TARGET, output()
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)
    elif not target.is_file() or target.read_text() != data:
        raise SystemExit("Stale Android shared widget test envelopes; run --write")
    print("Android shared widget envelopes: 31 cases, " + ("written" if args.write else "current"))
