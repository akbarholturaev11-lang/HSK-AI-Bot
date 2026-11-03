#!/usr/bin/env python3
"""Compare positive-study-time predictions locally; no DB, model export or dispatch."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.smart_reminder_offline import Dataset, OfflineError, evaluate_dataset

MAX_BYTES = 16*1024*1024


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "offline_arguments_invalid\n")


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--cutoff", required=True, help="Aware ISO timestamp separating training and later evaluation")
    parser.add_argument("--min-group-accounts", required=True, type=int)
    parser.add_argument("--neighbors", default=5, type=int)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file():
            raise OfflineError("offline_input_unavailable")
        with args.input.open("rb") as source:
            raw = source.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise OfflineError("offline_input_too_large")
        dataset = Dataset.model_validate_json(raw)
        report = evaluate_dataset(dataset,cutoff=datetime.fromisoformat(args.cutoff),
            minimum_accounts=args.min_group_accounts,neighbors=args.neighbors,now=datetime.now(timezone.utc))
    except OfflineError as error:
        print(str(error),file=sys.stderr)
        return 2
    except Exception:
        # Validation/paths/input values can contain private data. Never echo them.
        print("offline_dataset_invalid",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
