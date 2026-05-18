import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "evaluation_outputs" / "pro_engine"
DEFAULT_BENCHMARK_PATH = BACKEND_DIR / "evaluation_inputs" / "pro_small_benchmark.json"

import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from src.models.cmie_engine import CMIEEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small manually curated multimodal benchmark against the PRO/CMIE engine."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=DEFAULT_BENCHMARK_PATH,
        help="Path to a JSON benchmark file with labeled multimodal cases.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Maximum number of cases to run in one benchmark pass.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory where evaluation artifacts should be written.",
    )
    return parser.parse_args()


def load_cases(path: Path) -> List[Dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "cases" not in payload:
        raise ValueError("Benchmark JSON must be an object containing a 'cases' list.")
    cases = payload["cases"]
    if not isinstance(cases, list):
        raise ValueError("'cases' must be a list.")
    return cases


def compute_metrics(records: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(records)
    correct = sum(1 for item in records if item["correct"])
    accuracy = correct / total if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "accuracy_percent": round(accuracy * 100, 2),
    }


def main() -> None:
    args = parse_args()
    if not args.benchmark.exists():
        raise FileNotFoundError(
            f"Benchmark file not found: {args.benchmark}\n"
            "Please create it from the provided template before running."
        )

    raw_cases = load_cases(args.benchmark)
    selected_cases = raw_cases[: args.limit]
    run_dir = args.output_root / f"small_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    engine = CMIEEngine()
    records = []

    for idx, case in enumerate(selected_cases, start=1):
        text = str(case.get("text", "") or "")
        image_path = str(case.get("image_path", "") or "")
        video_path = str(case.get("video_path", "") or "")
        expected_is_fake = bool(case.get("label_is_fake", False))

        result = engine.detect(
            text=text,
            image_path=image_path if image_path else None,
            video_path=video_path if video_path else None,
        )
        predicted_is_fake = bool(result.get("is_fake", False))
        record = {
            "id": case.get("id", f"case_{idx}"),
            "category": case.get("category", "unspecified"),
            "expected_is_fake": expected_is_fake,
            "predicted_is_fake": predicted_is_fake,
            "correct": predicted_is_fake == expected_is_fake,
            "confidence": float(result.get("confidence", 0.0)),
            "text_preview": text[:120].replace("\n", " "),
            "image_path": image_path,
            "video_path": video_path,
            "reasoning": str(result.get("reasoning", "")),
        }
        records.append(record)
        print(
            f"[{idx}/{len(selected_cases)}] {record['id']} "
            f"expected={expected_is_fake} predicted={predicted_is_fake} "
            f"confidence={record['confidence']}"
        )

    metrics = compute_metrics(records)
    (run_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "benchmark_path": str(args.benchmark),
                "selected_cases": len(selected_cases),
                "metrics": metrics,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with (run_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()) if records else [])
        if records:
            writer.writeheader()
            writer.writerows(records)

    print(f"Artifacts written to: {run_dir}")


if __name__ == "__main__":
    main()
