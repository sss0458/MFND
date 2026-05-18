import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError as exc:
    plt = None
    HAS_MATPLOTLIB = False
    print(f"⚠️ matplotlib 不可用，图表将回退到 Pillow 绘制: {exc}")


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from src.data_loader.processor import MultimodalProcessor
from src.models.detector import MFNDManager


DATASET_NAME = "polsci/fake-news"
DATASET_CONFIG = "default"
DATASET_SPLIT = "train"
DATASET_VIEWER_BASE = "https://datasets-server.huggingface.co"
PAGE_SIZE = 100
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "evaluation_outputs" / "fast_engine"


def load_font(size: int = 18):
    for font_name in ("Arial Unicode.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = load_font(24)
LABEL_FONT = load_font(18)
SMALL_FONT = load_font(14)


def fetch_dataset_rows(cache_path: Path) -> List[Dict[str, object]]:
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if isinstance(cached, list) and cached:
            return cached

    session = requests.Session()
    size_resp = session.get(
        f"{DATASET_VIEWER_BASE}/size",
        params={"dataset": DATASET_NAME},
        timeout=30,
    )
    size_resp.raise_for_status()
    total_rows = size_resp.json()["size"]["dataset"]["num_rows"]

    fetched_rows: List[Dict[str, object]] = []
    for offset in range(0, total_rows, PAGE_SIZE):
        resp = session.get(
            f"{DATASET_VIEWER_BASE}/rows",
            params={
                "dataset": DATASET_NAME,
                "config": DATASET_CONFIG,
                "split": DATASET_SPLIT,
                "offset": offset,
                "length": PAGE_SIZE,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        for item in payload.get("rows", []):
            row = item.get("row", {})
            fetched_rows.append(
                {
                    "row_idx": item.get("row_idx"),
                    "text": row.get("text", ""),
                    "label": int(row.get("label", 0)),
                }
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(fetched_rows, handle, ensure_ascii=False, indent=2)
    return fetched_rows


def compute_metrics(records: List[Dict[str, object]]) -> Dict[str, object]:
    tn = fp = fn = tp = 0
    for record in records:
        true_label = int(record["true_label"])
        pred_label = int(record["pred_label"])
        if true_label == 0 and pred_label == 0:
            tn += 1
        elif true_label == 0 and pred_label == 1:
            fp += 1
        elif true_label == 1 and pred_label == 0:
            fn += 1
        else:
            tp += 1

    total = len(records)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "total": total,
        "accuracy": accuracy,
        "accuracy_percent": round(accuracy * 100, 2),
        "precision": precision,
        "precision_percent": round(precision * 100, 2),
        "recall": recall,
        "recall_percent": round(recall * 100, 2),
        "f1": f1,
        "f1_percent": round(f1 * 100, 2),
        "confusion_matrix": {
            "true_legit_pred_legit": tn,
            "true_legit_pred_fake": fp,
            "true_fake_pred_legit": fn,
            "true_fake_pred_fake": tp,
        },
    }


def save_json(path: Path, payload: Dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def save_csv(path: Path, records: List[Dict[str, object]]) -> None:
    if not records:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def _draw_centered_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill="black") -> None:
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2
    draw.text((x, y), text, font=font, fill=fill)


def _save_pillow_confusion_matrix(matrix, output_path: Path, title: str) -> None:
    image = Image.new("RGB", (720, 560), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), title, font=TITLE_FONT, fill="black")

    start_x, start_y = 180, 120
    cell_size = 140
    labels_x = ["Pred Legit", "Pred Fake"]
    labels_y = ["True Legit", "True Fake"]
    max_value = max(max(row) for row in matrix) or 1

    for idx, label in enumerate(labels_x):
        _draw_centered_text(draw, (start_x + idx * cell_size, 80, start_x + (idx + 1) * cell_size, 115), label, LABEL_FONT)
    for idx, label in enumerate(labels_y):
        _draw_centered_text(draw, (40, start_y + idx * cell_size, 165, start_y + (idx + 1) * cell_size), label, LABEL_FONT)

    for row_idx in range(2):
        for col_idx in range(2):
            value = matrix[row_idx][col_idx]
            shade = int(255 - (value / max_value) * 160)
            color = (shade, shade + 20 if shade <= 235 else 255, 255)
            left = start_x + col_idx * cell_size
            top = start_y + row_idx * cell_size
            right = left + cell_size
            bottom = top + cell_size
            draw.rectangle((left, top, right, bottom), fill=color, outline="black", width=2)
            _draw_centered_text(draw, (left, top, right, bottom), str(value), TITLE_FONT)

    image.save(output_path)


def _save_pillow_grouped_bar_chart(
    series: List[Dict[str, object]],
    labels: List[str],
    output_path: Path,
    title: str,
    y_label: str,
    max_value: float = None,
) -> None:
    width, height = 860, 560
    margin_left, margin_top, margin_bottom, margin_right = 80, 80, 90, 40
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), title, font=TITLE_FONT, fill="black")
    draw.text((20, height / 2 - 20), y_label, font=LABEL_FONT, fill="black")

    draw.line((margin_left, margin_top, margin_left, margin_top + chart_height), fill="black", width=2)
    draw.line(
        (margin_left, margin_top + chart_height, margin_left + chart_width, margin_top + chart_height),
        fill="black",
        width=2,
    )

    current_max = max_value if max_value is not None else max(max(item["values"]) for item in series)
    current_max = max(current_max, 1.0)

    group_width = chart_width / max(len(labels), 1)
    bar_width = max(int(group_width / (len(series) + 1)), 18)

    for tick in range(6):
        tick_value = current_max * tick / 5
        y = margin_top + chart_height - (tick_value / current_max) * chart_height
        draw.line((margin_left - 5, y, margin_left + chart_width, y), fill="#dddddd", width=1)
        draw.text((15, y - 8), f"{tick_value:.0f}", font=SMALL_FONT, fill="black")

    for label_idx, label in enumerate(labels):
        group_left = margin_left + label_idx * group_width
        label_box = (group_left, margin_top + chart_height + 10, group_left + group_width, margin_top + chart_height + 40)
        _draw_centered_text(draw, label_box, label, LABEL_FONT)

        for series_idx, item in enumerate(series):
            value = item["values"][label_idx]
            bar_left = group_left + 18 + series_idx * bar_width
            bar_right = bar_left + bar_width - 8
            bar_height = (value / current_max) * chart_height
            bar_top = margin_top + chart_height - bar_height
            draw.rectangle((bar_left, bar_top, bar_right, margin_top + chart_height), fill=item["color"], outline="black")
            value_box = (bar_left - 8, bar_top - 24, bar_right + 8, bar_top - 4)
            _draw_centered_text(draw, value_box, f"{value:.1f}" if isinstance(value, float) else str(value), SMALL_FONT)

    legend_x = width - 220
    legend_y = 24
    for idx, item in enumerate(series):
        top = legend_y + idx * 28
        draw.rectangle((legend_x, top, legend_x + 20, top + 20), fill=item["color"], outline="black")
        draw.text((legend_x + 28, top), item["name"], font=SMALL_FONT, fill="black")

    image.save(output_path)


def plot_confusion_matrix(metrics: Dict[str, object], output_path: Path, title: str) -> None:
    cm = metrics["confusion_matrix"]
    matrix = [
        [cm["true_legit_pred_legit"], cm["true_legit_pred_fake"]],
        [cm["true_fake_pred_legit"], cm["true_fake_pred_fake"]],
    ]

    if not HAS_MATPLOTLIB:
        _save_pillow_confusion_matrix(matrix, output_path, title)
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(matrix, cmap="Blues")
    plt.colorbar(image, ax=ax)
    ax.set_xticks([0, 1], labels=["Pred Legit", "Pred Fake"])
    ax.set_yticks([0, 1], labels=["True Legit", "True Fake"])
    ax.set_title(title)

    for row_idx in range(2):
        for col_idx in range(2):
            ax.text(col_idx, row_idx, str(matrix[row_idx][col_idx]), ha="center", va="center", color="black")

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_confidence_distribution(records: List[Dict[str, object]], output_path: Path, title: str) -> None:
    correct = [float(item["confidence"]) for item in records if item["correct"]]
    wrong = [float(item["confidence"]) for item in records if not item["correct"]]

    if not HAS_MATPLOTLIB:
        bins = list(range(0, 110, 10))
        correct_counts = [0] * (len(bins) - 1)
        wrong_counts = [0] * (len(bins) - 1)
        for value in correct:
            index = min(int(value // 10), len(correct_counts) - 1)
            correct_counts[index] += 1
        for value in wrong:
            index = min(int(value // 10), len(wrong_counts) - 1)
            wrong_counts[index] += 1

        _save_pillow_grouped_bar_chart(
            [
                {"name": "Correct", "values": correct_counts, "color": "#2e8b57"},
                {"name": "Wrong", "values": wrong_counts, "color": "#d1495b"},
            ],
            [f"{bins[idx]}-{bins[idx + 1]}" for idx in range(len(bins) - 1)],
            output_path,
            title,
            "Sample count",
        )
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    bins = [x for x in range(0, 110, 10)]
    if correct:
        ax.hist(correct, bins=bins, alpha=0.65, label="Correct", color="#2e8b57")
    if wrong:
        ax.hist(wrong, bins=bins, alpha=0.65, label="Wrong", color="#d1495b")
    ax.set_title(title)
    ax.set_xlabel("Reported confidence (%)")
    ax.set_ylabel("Sample count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_pred_vs_true(records: List[Dict[str, object]], output_path: Path, title: str) -> None:
    true_legit = sum(1 for item in records if item["true_label"] == 0)
    true_fake = sum(1 for item in records if item["true_label"] == 1)
    pred_legit = sum(1 for item in records if item["pred_label"] == 0)
    pred_fake = sum(1 for item in records if item["pred_label"] == 1)

    if not HAS_MATPLOTLIB:
        _save_pillow_grouped_bar_chart(
            [
                {"name": "True", "values": [true_legit, true_fake], "color": "#4c78a8"},
                {"name": "Pred", "values": [pred_legit, pred_fake], "color": "#f58518"},
            ],
            ["Legit", "Fake"],
            output_path,
            title,
            "Sample count",
        )
        return

    x_positions = [0, 1]
    width = 0.35

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([x - width / 2 for x in x_positions], [true_legit, true_fake], width=width, label="True", color="#4c78a8")
    ax.bar([x + width / 2 for x in x_positions], [pred_legit, pred_fake], width=width, label="Pred", color="#f58518")
    ax.set_xticks(x_positions, labels=["Legit", "Fake"])
    ax.set_ylabel("Sample count")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_mode_comparison(summary_rows: List[Dict[str, object]], output_path: Path) -> None:
    labels = [item["mode"] for item in summary_rows]
    accuracies = [item["accuracy_percent"] for item in summary_rows]
    f1_scores = [item["f1_percent"] for item in summary_rows]

    if not HAS_MATPLOTLIB:
        _save_pillow_grouped_bar_chart(
            [
                {"name": "Accuracy", "values": accuracies, "color": "#4c78a8"},
                {"name": "F1", "values": f1_scores, "color": "#54a24b"},
            ],
            labels,
            output_path,
            "FAST engine mode comparison",
            "Score (%)",
            max_value=100.0,
        )
        return

    x_positions = list(range(len(labels)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([x - width / 2 for x in x_positions], accuracies, width=width, label="Accuracy", color="#4c78a8")
    ax.bar([x + width / 2 for x in x_positions], f1_scores, width=width, label="F1", color="#54a24b")
    ax.set_xticks(x_positions, labels=labels)
    ax.set_ylabel("Score (%)")
    ax.set_title("FAST engine mode comparison")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def evaluate_mode(
    mode: str,
    samples: List[Dict[str, object]],
    output_dir: Path,
) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    processor = MultimodalProcessor(target_size=(224, 224))
    manager = MFNDManager(mode=mode)

    records: List[Dict[str, object]] = []
    total = len(samples)
    for idx, sample in enumerate(samples, start=1):
        cleaned_text = processor.clean_text(sample["text"])
        result = manager.detect(text=cleaned_text)
        pred_label = 1 if result["is_fake"] else 0
        record = {
            "row_idx": sample["row_idx"],
            "true_label": int(sample["label"]),
            "pred_label": pred_label,
            "true_label_name": "fake" if int(sample["label"]) == 1 else "legit",
            "pred_label_name": "fake" if pred_label == 1 else "legit",
            "confidence": float(result["confidence"]),
            "correct": pred_label == int(sample["label"]),
            "engine_mode": manager.mode,
            "text_preview": cleaned_text[:180].replace("\n", " "),
        }
        records.append(record)

        if idx == total or idx % 20 == 0:
            print(f"[{mode}] progress: {idx}/{total}")

    metrics = compute_metrics(records)
    misclassified = sorted(
        (item for item in records if not item["correct"]),
        key=lambda item: float(item["confidence"]),
        reverse=True,
    )[:10]

    summary = {
        "mode": mode,
        "mode_description": manager.describe_mode(),
        "text_model_name": getattr(manager, "text_compatible_model_name", None),
        "text_input_style": getattr(manager, "text_compatible_input_style", None),
        "text_ensemble_enabled": getattr(manager, "text_ensemble_enabled", False),
        "text_ensemble_secondary_model_name": getattr(
            manager,
            "text_ensemble_secondary_model_name",
            None,
        ),
        "text_ensemble_secondary_input_style": getattr(
            manager,
            "text_ensemble_secondary_input_style",
            None,
        ),
        "text_ensemble_primary_weight": getattr(manager, "text_ensemble_primary_weight", None),
        "text_ensemble_fake_threshold": getattr(manager, "text_ensemble_fake_threshold", None),
        "metrics": metrics,
        "misclassified_top10": misclassified,
    }

    save_csv(output_dir / "predictions.csv", records)
    save_json(output_dir / "predictions.json", {"mode": mode, "records": records})
    save_json(output_dir / "metrics_summary.json", summary)
    plot_confusion_matrix(metrics, output_dir / "confusion_matrix.png", f"{mode} confusion matrix")
    plot_confidence_distribution(records, output_dir / "confidence_distribution.png", f"{mode} confidence distribution")
    plot_pred_vs_true(records, output_dir / "pred_vs_true.png", f"{mode} prediction vs truth")

    return summary


def print_summary(summary: Dict[str, object]) -> None:
    metrics = summary["metrics"]
    print(
        f"{summary['mode']}: accuracy={metrics['accuracy_percent']}% "
        f"precision={metrics['precision_percent']}% "
        f"recall={metrics['recall_percent']}% "
        f"f1={metrics['f1_percent']}%"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the FAST engine against polsci/fake-news.")
    parser.add_argument("--limit", type=int, default=None, help="Only evaluate the first N samples.")
    parser.add_argument(
        "--replace-threshold",
        type=float,
        default=55.0,
        help="Trigger replacement mode evaluation when baseline accuracy is below or equal to this percentage.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory where evaluation artifacts should be written.",
    )
    parser.add_argument(
        "--skip-replacement",
        action="store_true",
        help="Only run the baseline legacy evaluation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_kind = "smoke" if args.limit else "full"
    run_dir = args.output_root / f"{run_kind}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cache_path = args.output_root / "dataset_cache" / "polsci_fake_news_train.json"
    rows = fetch_dataset_rows(cache_path)
    selected_rows = rows[: args.limit] if args.limit else rows

    save_json(
        run_dir / "dataset_snapshot.json",
        {
            "dataset": DATASET_NAME,
            "config": DATASET_CONFIG,
            "split": DATASET_SPLIT,
            "total_cached_rows": len(rows),
            "selected_rows": len(selected_rows),
            "rows": selected_rows,
        },
    )
    shutil.copyfile(cache_path, run_dir / "dataset_cache.json")

    baseline_dir = run_dir / "baseline_legacy_fusion"
    baseline_summary = evaluate_mode("legacy_fusion", selected_rows, baseline_dir)
    print_summary(baseline_summary)

    overall_summary = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "selected_rows": len(selected_rows),
        "replace_threshold_percent": args.replace_threshold,
        "fast_text_model_name": os.environ.get("FAST_TEXT_MODEL_NAME"),
        "fast_text_input_style": os.environ.get("FAST_TEXT_INPUT_STYLE"),
        "fast_text_ensemble_enabled": os.environ.get("FAST_TEXT_ENSEMBLE_ENABLED"),
        "fast_text_ensemble_secondary_model_name": os.environ.get("FAST_TEXT_ENSEMBLE_SECONDARY_MODEL_NAME"),
        "fast_text_ensemble_primary_weight": os.environ.get("FAST_TEXT_ENSEMBLE_PRIMARY_WEIGHT"),
        "fast_text_ensemble_fake_threshold": os.environ.get("FAST_TEXT_ENSEMBLE_FAKE_THRESHOLD"),
        "baseline": baseline_summary,
        "replacement_triggered": baseline_summary["metrics"]["accuracy_percent"] <= args.replace_threshold,
    }

    comparison_rows = [
        {
            "mode": baseline_summary["mode"],
            "accuracy_percent": baseline_summary["metrics"]["accuracy_percent"],
            "f1_percent": baseline_summary["metrics"]["f1_percent"],
        }
    ]

    if overall_summary["replacement_triggered"] and not args.skip_replacement:
        replacement_dir = run_dir / "replacement_text_compatible"
        replacement_summary = evaluate_mode("text_compatible", selected_rows, replacement_dir)
        print_summary(replacement_summary)
        overall_summary["replacement"] = replacement_summary
        overall_summary["improvement"] = {
            "accuracy_delta_percent": round(
                replacement_summary["metrics"]["accuracy_percent"] - baseline_summary["metrics"]["accuracy_percent"],
                2,
            ),
            "f1_delta_percent": round(
                replacement_summary["metrics"]["f1_percent"] - baseline_summary["metrics"]["f1_percent"],
                2,
            ),
        }
        comparison_rows.append(
            {
                "mode": replacement_summary["mode"],
                "accuracy_percent": replacement_summary["metrics"]["accuracy_percent"],
                "f1_percent": replacement_summary["metrics"]["f1_percent"],
            }
        )
        plot_mode_comparison(comparison_rows, run_dir / "mode_comparison.png")
    else:
        overall_summary["replacement"] = None
        overall_summary["improvement"] = None

    save_json(run_dir / "run_summary.json", overall_summary)
    print(f"Artifacts written to: {run_dir}")


if __name__ == "__main__":
    main()
