import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from evaluate_fast_engine import (
    DEFAULT_OUTPUT_ROOT,
    DATASET_CONFIG,
    DATASET_NAME,
    DATASET_SPLIT,
    evaluate_mode,
    fetch_dataset_rows,
    plot_mode_comparison,
    print_summary,
    save_json,
)


TOPIC_KEYWORDS = {
    "politics": [
        "trump",
        "president",
        "white house",
        "senate",
        "congress",
        "election",
        "government",
        "minister",
        "immigration",
        "policy",
    ],
    "technology": [
        "facebook",
        "twitter",
        "google",
        "apple",
        "iphone",
        "android",
        "nintendo",
        "software",
        "internet",
        "messenger",
        "app",
    ],
    "health_science": [
        "study",
        "research",
        "scientists",
        "nasa",
        "mars",
        "medical",
        "health",
        "doctor",
        "disease",
        "vaccine",
    ],
    "sports_entertainment": [
        "game",
        "season",
        "movie",
        "film",
        "show",
        "actor",
        "actress",
        "sports",
        "nba",
        "nfl",
        "olympic",
        "lebron",
        "demi lovato",
    ],
    "business_society": [
        "uber",
        "company",
        "market",
        "bank",
        "industry",
        "economy",
        "business",
        "taxi",
        "emissions",
        "california",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small topic-stratified FAST benchmark on cached fake-news rows."
    )
    parser.add_argument(
        "--limit-per-label",
        type=int,
        default=8,
        help="Maximum number of legit/fake samples to use for each topic bucket.",
    )
    parser.add_argument(
        "--modes",
        type=str,
        default="legacy_fusion,text_compatible",
        help="Comma-separated FAST modes to evaluate.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT.parent / "fast_topic_benchmark",
        help="Directory where benchmark artifacts should be written.",
    )
    return parser.parse_args()


def assign_topic(text: str) -> str:
    lowered = (text or "").lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return topic
    return ""


def build_topic_buckets(rows: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    buckets: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        topic = assign_topic(str(row.get("text", "")))
        if topic:
            enriched = dict(row)
            enriched["topic"] = topic
            buckets[topic].append(enriched)
    return buckets


def select_balanced_samples(
    buckets: Dict[str, List[Dict[str, object]]],
    limit_per_label: int,
) -> Dict[str, List[Dict[str, object]]]:
    selected: Dict[str, List[Dict[str, object]]] = {}
    for topic, rows in buckets.items():
        legit = [row for row in rows if int(row.get("label", 0)) == 0][:limit_per_label]
        fake = [row for row in rows if int(row.get("label", 0)) == 1][:limit_per_label]
        picked = legit + fake
        if picked:
            selected[topic] = picked
    return selected


def main() -> None:
    args = parse_args()
    modes = [item.strip() for item in args.modes.split(",") if item.strip()]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.output_root / f"topic_smoke_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cache_path = DEFAULT_OUTPUT_ROOT / "dataset_cache" / "polsci_fake_news_train.json"
    rows = fetch_dataset_rows(cache_path)
    buckets = build_topic_buckets(rows)
    selected = select_balanced_samples(buckets, args.limit_per_label)

    selection_summary = {
        topic: {
            "selected_total": len(topic_rows),
            "selected_legit": sum(1 for row in topic_rows if int(row["label"]) == 0),
            "selected_fake": sum(1 for row in topic_rows if int(row["label"]) == 1),
        }
        for topic, topic_rows in selected.items()
    }

    save_json(
        run_dir / "topic_selection.json",
        {
            "dataset": DATASET_NAME,
            "config": DATASET_CONFIG,
            "split": DATASET_SPLIT,
            "limit_per_label": args.limit_per_label,
            "topics": selection_summary,
        },
    )

    overall_rows: List[Dict[str, object]] = []
    for topic_rows in selected.values():
        overall_rows.extend(topic_rows)

    run_summary = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "limit_per_label": args.limit_per_label,
        "topics": selection_summary,
        "modes": {},
    }

    for mode in modes:
        mode_dir = run_dir / mode
        topic_metrics = {}
        comparison_rows = []

        for topic, topic_rows in selected.items():
            summary = evaluate_mode(mode, topic_rows, mode_dir / topic)
            print(f"[{mode}] topic={topic}")
            print_summary(summary)
            topic_metrics[topic] = summary
            comparison_rows.append(
                {
                    "mode": topic,
                    "accuracy_percent": summary["metrics"]["accuracy_percent"],
                    "f1_percent": summary["metrics"]["f1_percent"],
                }
            )

        overall_summary = evaluate_mode(mode, overall_rows, mode_dir / "overall")
        print(f"[{mode}] overall")
        print_summary(overall_summary)
        comparison_rows.append(
            {
                "mode": "overall",
                "accuracy_percent": overall_summary["metrics"]["accuracy_percent"],
                "f1_percent": overall_summary["metrics"]["f1_percent"],
            }
        )
        plot_mode_comparison(comparison_rows, mode_dir / "topic_mode_comparison.png")

        run_summary["modes"][mode] = {
            "per_topic": topic_metrics,
            "overall": overall_summary,
        }

    save_json(run_dir / "run_summary.json", run_summary)
    print(f"Artifacts written to: {run_dir}")


if __name__ == "__main__":
    main()
