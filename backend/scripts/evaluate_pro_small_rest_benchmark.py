import argparse
import base64
import csv
import json
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import dotenv_values, load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_ROOT = BACKEND_DIR / "evaluation_outputs" / "pro_engine_rest"
DEFAULT_BENCHMARK_PATH = BACKEND_DIR / "evaluation_inputs" / "pro_small_benchmark.json"
DEFAULT_ENV_PATH = BACKEND_DIR / "web_system" / ".env"
MODEL_NAME = "gemini-2.5-flash"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small manually curated multimodal benchmark against Gemini via REST."
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
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Per-request timeout in seconds.",
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
    successful = [item for item in records if item.get("success", False)]
    tp = sum(1 for item in successful if item["expected_is_fake"] and item["predicted_is_fake"])
    tn = sum(1 for item in successful if not item["expected_is_fake"] and not item["predicted_is_fake"])
    fp = sum(1 for item in successful if not item["expected_is_fake"] and item["predicted_is_fake"])
    fn = sum(1 for item in successful if item["expected_is_fake"] and not item["predicted_is_fake"])
    evaluated = len(successful)
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


def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    if DEFAULT_ENV_PATH.exists():
        key = dotenv_values(DEFAULT_ENV_PATH).get("GEMINI_API_KEY")
        if key:
            return key
    raise RuntimeError("GEMINI_API_KEY not found in environment or backend/web_system/.env")


def build_parts(text: str, image_path: str) -> List[Dict[str, object]]:
    prompt = (
        "你是一个资深的多模态假新闻与脱离语境检测专家。"
        "请执行三步分析："
        "1. 分别提取文本和图像中的关键实体；"
        "2. 分析这些实体在客观现实中是否逻辑共存，重点寻找张冠李戴、类别错配、场景冲突；"
        "3. 最终判断该新闻是否为虚假或脱离语境信息。"
        "请只返回 JSON，不要输出 Markdown。"
        '格式为 {"is_fake": true/false, "confidence": 0-100, "reasoning": "中文分析"}。'
    )

    parts: List[Dict[str, object]] = [{"text": prompt}]
    if text:
        parts.append({"text": f"待测新闻文本内容：{text}"})

    if image_path:
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        encoded = base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")
        parts.append({"inline_data": {"mime_type": mime_type, "data": encoded}})
    return parts


def sanitize_error_message(message: str, api_key: str) -> str:
    if api_key:
        message = message.replace(api_key, "***")
    if "?key=" in message:
        prefix = message.split("?key=", 1)[0]
        return f"{prefix}?key=***"
    return message


def call_gemini(api_key: str, text: str, image_path: str, timeout: int) -> Dict[str, object]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": build_parts(text, image_path)}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    response = None
    for attempt in range(3):
        response = requests.post(url, json=payload, timeout=timeout)
        if response.status_code not in {429, 500, 502, 503, 504}:
            break
        if attempt < 2:
            time.sleep(2 ** attempt)
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No candidates returned: {json.dumps(data, ensure_ascii=False)}")
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts or "text" not in parts[0]:
        raise RuntimeError(f"No text content returned: {json.dumps(data, ensure_ascii=False)}")
    result_text = parts[0]["text"].strip()
    result = json.loads(result_text)
    return {
        "is_fake": bool(result.get("is_fake", False)),
        "confidence": float(result.get("confidence", 0.0)),
        "reasoning": str(result.get("reasoning", "")),
        "raw_response": data,
    }


def main() -> None:
    args = parse_args()
    if not args.benchmark.exists():
        raise FileNotFoundError(f"Benchmark file not found: {args.benchmark}")

    api_key = load_api_key()
    raw_cases = load_cases(args.benchmark)
    selected_cases = raw_cases[: args.limit]

    run_dir = args.output_root / f"small_rest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for idx, case in enumerate(selected_cases, start=1):
        text = str(case.get("text", "") or "")
        image_path = str(case.get("image_path", "") or "")
        expected_is_fake = bool(case.get("label_is_fake", False))

        try:
            result = call_gemini(api_key=api_key, text=text, image_path=image_path, timeout=args.timeout)
            predicted_is_fake = bool(result.get("is_fake", False))
            confidence = float(result.get("confidence", 0.0))
            reasoning = str(result.get("reasoning", ""))
            error = ""
            success = True
        except Exception as exc:
            predicted_is_fake = False
            confidence = 0.0
            reasoning = ""
            error = sanitize_error_message(str(exc), api_key)
            success = False

        record = {
            "id": case.get("id", f"case_{idx}"),
            "category": case.get("category", "unspecified"),
            "expected_is_fake": expected_is_fake,
            "predicted_is_fake": predicted_is_fake,
            "correct": success and (predicted_is_fake == expected_is_fake),
            "success": success,
            "confidence": confidence,
            "text_preview": text[:120].replace("\n", " "),
            "image_path": image_path,
            "reasoning": reasoning,
            "error": error,
        }
        records.append(record)
        print(
            f"[{idx}/{len(selected_cases)}] {record['id']} expected={expected_is_fake} "
            f"predicted={predicted_is_fake} confidence={confidence} error={bool(error)}",
            flush=True,
        )

    metrics = compute_metrics(records)
    (run_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "benchmark_path": str(args.benchmark),
                "selected_cases": len(selected_cases),
                "model": MODEL_NAME,
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

    print(f"Artifacts written to: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
