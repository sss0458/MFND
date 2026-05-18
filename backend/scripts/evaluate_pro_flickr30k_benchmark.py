import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

from evaluate_pro_small_rest_benchmark import call_gemini, load_api_key


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATASET_VIEWER_BASE = "https://datasets-server.huggingface.co"
DATASET_NAME = "nlphuji/flickr30k"
DATASET_CONFIG = "TEST"
DATASET_SPLIT = "test"
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "evaluation_outputs" / "pro_flickr30k_benchmark"


def fetch_rows(limit: int = 20) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    offset = 0
    while len(rows) < limit:
        remaining = limit - len(rows)
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
                        "length": min(20, remaining),
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
            captions = row.get("caption") or []
            image_src = image.get("src")
            if not image_src or not captions:
                continue
            rows.append(
                {
                    "row_idx": item.get("row_idx"),
                    "img_id": row.get("img_id"),
                    "filename": row.get("filename"),
                    "image_src": image_src,
                    "caption": str(captions[0]),
                }
            )
            if len(rows) >= limit:
                break
        offset += min(20, remaining)
    return rows


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
            "id": f"flickr_real_{idx:03d}",
            "group": idx,
            "kind": "aligned",
            "expected_is_fake": False,
            "text": row["caption"],
            "image_path": row["image_path"],
            "img_id": row["img_id"],
            "source_row_idx": row["row_idx"],
        }
        mismatch_row = rows[(idx + 7) % total]
        if mismatch_row["img_id"] == row["img_id"]:
            mismatch_row = rows[(idx + 11) % total]
        mismatched = {
            "id": f"flickr_fake_{idx:03d}",
            "group": idx,
            "kind": "mismatched",
            "expected_is_fake": True,
            "text": mismatch_row["caption"],
            "image_path": row["image_path"],
            "img_id": row["img_id"],
            "mismatch_img_id": mismatch_row["img_id"],
            "source_row_idx": row["row_idx"],
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
            last_error = str(exc)
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


def compute_group_metrics(records: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    groups: Dict[str, List[Dict[str, object]]] = {"aligned": [], "mismatched": []}
    for record in records:
        groups.setdefault(record["kind"], []).append(record)
    summary: Dict[str, Dict[str, object]] = {}
    for kind, items in groups.items():
        successful = [item for item in items if item.get("success", False)]
        correct = sum(1 for item in successful if item["correct"])
        accuracy = correct / len(successful) if successful else 0.0
        summary[kind] = {
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
    selected_rows = fetch_rows(limit=20)
    if len(selected_rows) < 20:
        raise RuntimeError(f"Only fetched {len(selected_rows)} valid Flickr30k rows.")

    for row in selected_rows:
        local_name = f"{row['img_id']}_{row['filename']}"
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
            "img_id": case["img_id"],
            "source_row_idx": case["source_row_idx"],
            "mismatch_img_id": case.get("mismatch_img_id", ""),
            "mismatch_row_idx": case.get("mismatch_row_idx", ""),
            "expected_is_fake": case["expected_is_fake"],
            "predicted_is_fake": result["predicted_is_fake"],
            "correct": result["success"] and (case["expected_is_fake"] == result["predicted_is_fake"]),
            "success": result["success"],
            "confidence": result["confidence"],
            "text_preview": str(case["text"])[:160],
            "image_path": case["image_path"],
            "reasoning": result["reasoning"],
            "error": result["error"],
        }
        records.append(record)
        print(
            f"[{idx}/{len(cases)}] {record['id']} kind={record['kind']} "
            f"expected={record['expected_is_fake']} predicted={record['predicted_is_fake']} "
            f"success={record['success']} confidence={record['confidence']}",
            flush=True,
        )

    summary = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "sampled_rows": selected_rows,
        "total_cases": len(cases),
        "metrics": compute_metrics(records),
        "group_metrics": compute_group_metrics(records),
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
