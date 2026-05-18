import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

from evaluate_pro_small_rest_benchmark import call_gemini, load_api_key, sanitize_error_message


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATASET_VIEWER_BASE = "https://datasets-server.huggingface.co"
DATASET_NAME = "thiagohersan/newsdata-images"
DATASET_CONFIG = "default"
DATASET_SPLIT = "newsdata"
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "evaluation_outputs" / "pro_newsdata_benchmark"
TARGET_ARTICLES = 24


def fetch_rows(limit: int = TARGET_ARTICLES) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    offset = 0
    while len(rows) < limit:
        payload = None
        for attempt in range(3):
            try:
                resp = requests.get(
                    f"{DATASET_VIEWER_BASE}/rows",
                    params={
                        "dataset": DATASET_NAME,
                        "config": DATASET_CONFIG,
                        "split": DATASET_SPLIT,
                        "offset": offset,
                        "length": min(20, limit - len(rows)),
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                payload = resp.json()
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

        if payload is None:
            break
        page_rows = payload.get("rows", [])
        if not page_rows:
            break

        for item in page_rows:
            row = item.get("row", {})
            image = row.get("image") or {}
            image_src = image.get("src")
            title = str(row.get("title", "") or "").strip()
            description = str(row.get("description", "") or "").strip()
            if not image_src or not title:
                continue
            rows.append(
                {
                    "row_idx": item.get("row_idx"),
                    "article_id": row.get("article_id"),
                    "title": title,
                    "description": description,
                    "source_name": str(row.get("source_name", "") or ""),
                    "pubDate": str(row.get("pubDate", "") or ""),
                    "style": str(row.get("style", "") or ""),
                    "image_src": image_src,
                }
            )
            if len(rows) >= limit:
                break
        offset += min(20, limit - len(rows))
    return rows


def build_news_text(row: Dict[str, object]) -> str:
    title = str(row["title"]).strip()
    description = str(row.get("description", "") or "").strip()
    source_name = str(row.get("source_name", "") or "").strip()
    pub_date = str(row.get("pubDate", "") or "").strip()
    if len(description) > 280:
        description = description[:280].rsplit(" ", 1)[0] + "..."

    parts = [f"标题：{title}"]
    if description:
        parts.append(f"摘要：{description}")
    if source_name:
        parts.append(f"来源：{source_name}")
    if pub_date:
        parts.append(f"发布日期：{pub_date}")
    return "\n".join(parts)


def download_image(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            path.write_bytes(resp.content)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def build_cases(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    cases: List[Dict[str, object]] = []
    total = len(rows)
    for idx, row in enumerate(rows):
        aligned = {
            "id": f"news_real_{idx:03d}",
            "group": idx,
            "kind": "aligned_news",
            "expected_is_fake": False,
            "text": build_news_text(row),
            "image_path": row["image_path"],
            "article_id": row["article_id"],
            "source_name": row["source_name"],
            "style": row["style"],
            "row_idx": row["row_idx"],
        }
        mismatch_row = rows[(idx + 9) % total]
        if mismatch_row["article_id"] == row["article_id"]:
            mismatch_row = rows[(idx + 13) % total]
        mismatched = {
            "id": f"news_fake_{idx:03d}",
            "group": idx,
            "kind": "mismatched_news",
            "expected_is_fake": True,
            "text": build_news_text(mismatch_row),
            "image_path": row["image_path"],
            "article_id": row["article_id"],
            "source_name": row["source_name"],
            "style": row["style"],
            "row_idx": row["row_idx"],
            "mismatch_article_id": mismatch_row["article_id"],
            "mismatch_source_name": mismatch_row["source_name"],
            "mismatch_style": mismatch_row["style"],
            "mismatch_row_idx": mismatch_row["row_idx"],
        }
        cases.extend([aligned, mismatched])
    return cases


def run_case(api_key: str, case: Dict[str, object], timeout: int = 90) -> Dict[str, object]:
    last_error = ""
    for attempt in range(2):
        try:
            result = call_gemini(
                api_key=api_key,
                text=str(case["text"]),
                image_path=str(case["image_path"]),
                timeout=timeout,
            )
            return {
                "predicted_is_fake": bool(result["is_fake"]),
                "confidence": float(result["confidence"]),
                "reasoning": str(result["reasoning"]),
                "success": True,
                "error": "",
            }
        except Exception as exc:
            last_error = sanitize_error_message(str(exc), api_key)
            if attempt == 1:
                break
            time.sleep(3)
    return {
        "predicted_is_fake": False,
        "confidence": 0.0,
        "reasoning": "",
        "success": False,
        "error": last_error,
    }


def compute_metrics(records: List[Dict[str, object]]) -> Dict[str, object]:
    successful = [item for item in records if item.get("success", False)]
    total = len(records)
    evaluated = len(successful)
    tp = sum(1 for item in successful if item["expected_is_fake"] and item["predicted_is_fake"])
    tn = sum(1 for item in successful if not item["expected_is_fake"] and not item["predicted_is_fake"])
    fp = sum(1 for item in successful if not item["expected_is_fake"] and item["predicted_is_fake"])
    fn = sum(1 for item in successful if item["expected_is_fake"] and not item["predicted_is_fake"])
    accuracy = (tp + tn) / evaluated if evaluated else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "total": total,
        "evaluated_successfully": evaluated,
        "failed_requests": total - evaluated,
        "correct": tp + tn,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy_percent": round(accuracy * 100, 2),
        "precision_percent": round(precision * 100, 2),
        "recall_percent": round(recall * 100, 2),
        "f1_percent": round(f1 * 100, 2),
    }


def compute_kind_metrics(records: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    summary: Dict[str, Dict[str, object]] = {}
    for kind in sorted({record["kind"] for record in records}):
        items = [record for record in records if record["kind"] == kind]
        successful = [item for item in items if item.get("success", False)]
        correct = sum(1 for item in successful if item["correct"])
        accuracy = correct / len(successful) if successful else 0.0
        summary[kind] = {
            "total": len(items),
            "evaluated_successfully": len(successful),
            "accuracy_percent": round(accuracy * 100, 2),
        }
    return summary


def compute_source_metrics(records: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    summary: Dict[str, Dict[str, object]] = {}
    for source_name in sorted({record["source_name"] for record in records}):
        items = [record for record in records if record["source_name"] == source_name]
        successful = [item for item in items if item.get("success", False)]
        correct = sum(1 for item in successful if item["correct"])
        accuracy = correct / len(successful) if successful else 0.0
        summary[source_name] = {
            "total": len(items),
            "evaluated_successfully": len(successful),
            "accuracy_percent": round(accuracy * 100, 2),
        }
    return summary


def main() -> None:
    output_dir = DEFAULT_OUTPUT_ROOT / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    api_key = load_api_key()
    selected_rows = fetch_rows(limit=TARGET_ARTICLES)
    if len(selected_rows) < TARGET_ARTICLES:
        raise RuntimeError(f"Only fetched {len(selected_rows)} valid rows from {DATASET_NAME}.")

    for row in selected_rows:
        local_name = f"{row['article_id']}.jpg"
        local_path = image_dir / local_name
        download_image(str(row["image_src"]), local_path)
        row["image_path"] = str(local_path)

    cases = build_cases(selected_rows)
    records: List[Dict[str, object]] = []

    for idx, case in enumerate(cases, start=1):
        result = run_case(api_key=api_key, case=case, timeout=90)
        record = {
            "id": case["id"],
            "group": case["group"],
            "kind": case["kind"],
            "article_id": case["article_id"],
            "row_idx": case["row_idx"],
            "source_name": case["source_name"],
            "style": case["style"],
            "mismatch_article_id": case.get("mismatch_article_id", ""),
            "mismatch_source_name": case.get("mismatch_source_name", ""),
            "mismatch_style": case.get("mismatch_style", ""),
            "mismatch_row_idx": case.get("mismatch_row_idx", ""),
            "expected_is_fake": case["expected_is_fake"],
            "predicted_is_fake": result["predicted_is_fake"],
            "correct": result["success"] and (case["expected_is_fake"] == result["predicted_is_fake"]),
            "success": result["success"],
            "confidence": result["confidence"],
            "text_preview": str(case["text"])[:220].replace("\n", " "),
            "image_path": case["image_path"],
            "reasoning": result["reasoning"],
            "error": result["error"],
        }
        records.append(record)
        print(
            f"[{idx}/{len(cases)}] {record['id']} source={record['source_name']} "
            f"kind={record['kind']} expected={record['expected_is_fake']} "
            f"predicted={record['predicted_is_fake']} success={record['success']} "
            f"confidence={record['confidence']}",
            flush=True,
        )

    summary = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "sampled_rows": selected_rows,
        "total_cases": len(cases),
        "metrics": compute_metrics(records),
        "kind_metrics": compute_kind_metrics(records),
        "source_metrics": compute_source_metrics(records),
        "records": records,
    }
    (output_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()) if records else [])
        if records:
            writer.writeheader()
            writer.writerows(records)

    print(f"Artifacts written to: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
