#!/usr/bin/env python3
"""Command-line runner for the OCR + agent pipeline.

This script is intended to be invoked by the Node.js backend to process
an uploaded medical bill. It performs the following steps:

1. Runs the OCR pipeline on the provided file path (PDF/image)
2. Feeds the resulting text into the agent pipeline
3. Optionally runs the debate simulation for the analyzed line items
4. Emits a single JSON object to stdout containing all relevant results

Example usage:
    python3 backend/run_pipeline_cli.py --file /tmp/bill.pdf --prompt "Focus on overpriced items"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill
from backend.agents.debate import DebateManager, generate_debate_summary

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OCR + agent pipeline and emit JSON results")
    parser.add_argument("--file", required=True, help="Path to the uploaded bill (PDF/image)")
    parser.add_argument("--prompt", default="", help="Optional user prompt/instructions")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use for all agents")
    parser.add_argument(
        "--max-debate-rounds",
        type=int,
        default=3,
        help="Number of fighter vs. hospital debate rounds (0 disables debate)",
    )
    parser.add_argument(
        "--no-debate",
        action="store_true",
        help="Skip the debate simulation even if analysis items exist",
    )
    return parser.parse_args()


def run_pipeline(file_path: Path, prompt: str, model: str, max_rounds: int, run_debate: bool) -> Dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info("Running OCR pipeline on %s", file_path)
    ocr_pipeline = OCRPipeline()
    ocr_output = ocr_pipeline.extract(str(file_path), return_pages=False)
    ocr_text = ocr_output if isinstance(ocr_output, str) else ocr_output.get("text", "")

    if not ocr_text.strip():
        raise ValueError("OCR pipeline produced empty text")

    logger.info("Running agent pipeline (model=%s)", model)
    pipeline_result = process_medical_bill(ocr_text=ocr_text, model=model)

    debate_transcript: List[Dict[str, Any]] = []
    debate_summary: Dict[str, str] | None = None

    if run_debate and pipeline_result.get("analysis"):
        rounds = max(1, max_rounds)
        logger.info("Running debate simulation (%s rounds)", rounds)
        debate_manager = DebateManager(max_rounds=rounds, model=model)
        debate_transcript = debate_manager.run_debate(
            bill_json=pipeline_result["analysis"],
            num_rounds=rounds,
        )
        try:
            debate_summary = generate_debate_summary(
                bill_json=pipeline_result["analysis"],
                debate_transcript=debate_transcript,
                model=model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Debate summary generation failed: %s", exc)

    return {
        "ocr_text": ocr_text,
        "prompt": prompt,
        "extraction": pipeline_result.get("extraction", []),
        "analysis": pipeline_result.get("analysis", []),
        "negotiation": pipeline_result.get("negotiation", {}),
        "summary_stats": pipeline_result.get("summary_stats", {}),
        "debate_transcript": debate_transcript,
        "debate_summary": debate_summary,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    try:
        result = run_pipeline(
            file_path=Path(args.file),
            prompt=args.prompt,
            model=args.model,
            max_rounds=args.max_debate_rounds,
            run_debate=not args.no_debate,
        )
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("Pipeline execution failed: %s", exc, exc_info=True)
        error_payload = {"error": str(exc)}
        json.dump(error_payload, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
