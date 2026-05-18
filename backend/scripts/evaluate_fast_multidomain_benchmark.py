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
    compute_metrics,
    evaluate_mode,
    fetch_dataset_rows,
    plot_confidence_distribution,
    plot_confusion_matrix,
    plot_mode_comparison,
    plot_pred_vs_true,
    print_summary,
    save_csv,
    save_json,
)


DOMAIN_KEYWORDS = {
    "politics": [
        "trump",
        "obama",
        "clinton",
        "white house",
        "president",
        "congress",
        "senate",
        "democrat",
        "republican",
        "government",
        "election",
        "campaign",
        "administration",
        "minister",
        "policy",
        "governor",
    ],
    "business": [
        "company",
        "market",
        "stock",
        "investor",
        "profit",
        "revenue",
        "business",
        "bank",
        "ceo",
        "advertis",
        "finance",
        "economy",
        "trade",
        "oil",
        "startup",
        "uber",
        "merger",
    ],
    "technology": [
        "facebook",
        "twitter",
        "google",
        "apple",
        "microsoft",
        "snapchat",
        "instagram",
        "software",
        "internet",
        "app",
        "iphone",
        "android",
        "robot",
        "tesla",
        "tech",
        "algorithm",
    ],
    "education": [
        "school",
        "student",
        "college",
        "university",
        "education",
        "teacher",
        "classroom",
        "campus",
        "professor",
        "scholarship",
        "academic",
    ],
    "sports": [
        "game",
        "season",
        "player",
        "coach",
        "league",
        "nba",
        "nfl",
        "mlb",
        "soccer",
        "olympic",
        "champion",
        "tournament",
        "tennis",
        "golf",
        "baseball",
        "football",
        "basketball",
    ],
    "entertainment_celebrity": [
        "movie",
        "film",
        "netflix",
        "series",
        "tv ",
        "television",
        "show",
        "award",
        "hollywood",
        "music",
        "song",
        "album",
        "actor",
        "actress",
        "singer",
        "celebrity",
        "star ",
        "oscars",
        "grammy",
        "katy perry",
        "taylor swift",
        "carrie fisher",
        "debbie reynolds",
        "elton john",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a multi-domain FAST benchmark on cached fake-news rows."
    )
    parser.add_argument(
        "--modes",
        type=str,
        default="legacy_fusion,text_compatible",
        help="Comma-separated FAST modes to evaluate.",
    )
    parser.add_argument(
        "--limit-per-label",
        type=int,
        default=None,
        help="Optional per-domain cap for each label. Default uses the maximum balanced count in each domain.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT.parent / "fast_multidomain_benchmark",
        help="Directory where benchmark artifacts should be written.",
    )
    return parser.parse_args()


def score_domain(text: str, keywords: List[str]) -> int:
    lowered = f" {(text or '').lower()} "
    return sum(1 for keyword in keywords if keyword in lowered)


def assign_domain(text: str) -> str:
    scores = {domain: score_domain(text, keywords) for domain, keywords in DOMAIN_KEYWORDS.items()}
    best_domain = max(scores, key=scores.get)
    return best_domain if scores[best_domain] > 0 else ""


def build_domain_buckets(rows: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    buckets: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        domain = assign_domain(str(row.get("text", "")))
        if not domain:
            continue
        enriched = dict(row)
        enriched["domain"] = domain
        buckets[domain].append(enriched)
    return buckets


def select_balanced_samples(
    buckets: Dict[str, List[Dict[str, object]]],
    limit_per_label: int | None,
) -> Dict[str, List[Dict[str, object]]]:
    selected: Dict[str, List[Dict[str, object]]] = {}
    for domain, rows in buckets.items():
        legit = [row for row in rows if int(row.get("label", 0)) == 0]
        fake = [row for row in rows if int(row.get("label", 0)) == 1]
        balanced_count = min(len(legit), len(fake))
        if limit_per_label is not None:
            balanced_count = min(balanced_count, limit_per_label)
        if balanced_count <= 0:
            continue
        selected[domain] = legit[:balanced_count] + fake[:balanced_count]
    return selected


def build_overall_summary_from_domain_outputs(
    mode: str,
    mode_dir: Path,
    domain_metrics: Dict[str, Dict[str, object]],
) -> Dict[str, object]:
    overall_dir = mode_dir / "overall"
    overall_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, object]] = []
    for domain in domain_metrics:
        predictions_path = mode_dir / domain / "predictions.json"
        payload = json.loads(predictions_path.read_text(encoding="utf-8"))
        records.extend(payload.get("records", []))

    metrics = compute_metrics(records)
    misclassified = sorted(
        (item for item in records if not item["correct"]),
        key=lambda item: float(item["confidence"]),
        reverse=True,
    )[:10]
    sample_summary = next(iter(domain_metrics.values()))
    summary = {
        "mode": mode,
        "mode_description": sample_summary["mode_description"],
        "text_model_name": sample_summary.get("text_model_name"),
        "text_input_style": sample_summary.get("text_input_style"),
        "text_ensemble_enabled": sample_summary.get("text_ensemble_enabled", False),
        "text_ensemble_secondary_model_name": sample_summary.get("text_ensemble_secondary_model_name"),
        "text_ensemble_secondary_input_style": sample_summary.get("text_ensemble_secondary_input_style"),
        "text_ensemble_primary_weight": sample_summary.get("text_ensemble_primary_weight"),
        "text_ensemble_fake_threshold": sample_summary.get("text_ensemble_fake_threshold"),
        "metrics": metrics,
        "misclassified_top10": misclassified,
    }

    save_csv(overall_dir / "predictions.csv", records)
    save_json(overall_dir / "predictions.json", {"mode": mode, "records": records})
    save_json(overall_dir / "metrics_summary.json", summary)
    plot_confusion_matrix(metrics, overall_dir / "confusion_matrix.png", f"{mode} overall confusion matrix")
    plot_confidence_distribution(records, overall_dir / "confidence_distribution.png", f"{mode} overall confidence distribution")
    plot_pred_vs_true(records, overall_dir / "pred_vs_true.png", f"{mode} overall prediction vs truth")
    return summary


def main() -> None:
    args = parse_args()
    modes = [item.strip() for item in args.modes.split(",") if item.strip()]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.output_root / f"multidomain_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cache_path = DEFAULT_OUTPUT_ROOT / "dataset_cache" / "polsci_fake_news_train.json"
    rows = fetch_dataset_rows(cache_path)
    buckets = build_domain_buckets(rows)
    selected = select_balanced_samples(buckets, args.limit_per_label)

    selection_summary = {}
    overall_rows: List[Dict[str, object]] = []
    for domain, domain_rows in selected.items():
        legit_count = sum(1 for row in domain_rows if int(row["label"]) == 0)
        fake_count = sum(1 for row in domain_rows if int(row["label"]) == 1)
        selection_summary[domain] = {
            "selected_total": len(domain_rows),
            "selected_legit": legit_count,
            "selected_fake": fake_count,
            "balanced_per_label": min(legit_count, fake_count),
        }
        overall_rows.extend(domain_rows)

    save_json(
        run_dir / "domain_selection.json",
        {
            "dataset": DATASET_NAME,
            "config": DATASET_CONFIG,
            "split": DATASET_SPLIT,
            "dataset_card_domains": [
                "technology",
                "education",
                "business",
                "sports",
                "politics",
                "entertainment",
                "celebrity",
            ],
            "implemented_domains": list(selected.keys()),
            "limit_per_label": args.limit_per_label,
            "domains": selection_summary,
        },
    )

    run_summary = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "dataset_card_domains": [
            "technology",
            "education",
            "business",
            "sports",
            "politics",
            "entertainment",
            "celebrity",
        ],
        "implemented_domains": list(selected.keys()),
        "limit_per_label": args.limit_per_label,
        "domains": selection_summary,
        "selected_rows": len(overall_rows),
        "modes": {},
    }

    for mode in modes:
        mode_dir = run_dir / mode
        domain_metrics = {}
        comparison_rows = []

        for domain, domain_rows in selected.items():
            summary = evaluate_mode(mode, domain_rows, mode_dir / domain)
            print(f"[{mode}] domain={domain}")
            print_summary(summary)
            domain_metrics[domain] = summary
            comparison_rows.append(
                {
                    "mode": domain,
                    "accuracy_percent": summary["metrics"]["accuracy_percent"],
                    "f1_percent": summary["metrics"]["f1_percent"],
                }
            )

        overall_summary = build_overall_summary_from_domain_outputs(mode, mode_dir, domain_metrics)
        print(f"[{mode}] overall")
        print_summary(overall_summary)
        comparison_rows.append(
            {
                "mode": "overall",
                "accuracy_percent": overall_summary["metrics"]["accuracy_percent"],
                "f1_percent": overall_summary["metrics"]["f1_percent"],
            }
        )
        plot_mode_comparison(comparison_rows, mode_dir / "multidomain_comparison.png")

        run_summary["modes"][mode] = {
            "per_domain": domain_metrics,
            "overall": overall_summary,
        }

    save_json(run_dir / "run_summary.json", run_summary)
    print(f"Artifacts written to: {run_dir}")


if __name__ == "__main__":
    main()
