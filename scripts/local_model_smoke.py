#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.llm import get_model_adapter  # noqa: E402
from app.services.chunking_service import ChunkingService  # noqa: E402

SAMPLE_TEXT = (
    "Although previous studies have suggested a correlation between sleep deprivation "
    "and reduced cognitive performance, the extent to which these findings generalize "
    "across real-world learning environments remains unclear. To address this gap, "
    "we analyze longitudinal study logs collected from undergraduate students over a "
    "six-week period."
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run one local model analysis and save normalized JSON.")
    parser.add_argument("--provider", default="mlx", choices=["mock", "mlx", "ollama"])
    parser.add_argument("--preset", default="gemma4-e4b-mlx")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp" / "local_model_smoke.json")
    args = parser.parse_args()

    os.environ["MODEL_PROVIDER"] = args.provider
    os.environ["MODEL_RUNTIME_CONFIG_PATH"] = str(ROOT / "tmp" / "model_runtime_smoke.json")
    os.environ["RAW_MODEL_OUTPUT_PATH"] = str(ROOT / "tmp" / "local_model_raw.txt")

    if args.input:
        text = args.input.read_text(encoding="utf-8")
    else:
        text = SAMPLE_TEXT

    runtime_config = Path(os.environ["MODEL_RUNTIME_CONFIG_PATH"])
    runtime_config.parent.mkdir(parents=True, exist_ok=True)
    runtime_config.write_text(json.dumps({"preset_id": args.preset, "provider": args.provider}, indent=2), encoding="utf-8")

    chunks = ChunkingService().chunk(text)
    result = await get_model_adapter().analyze_document("local-smoke", text, chunks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"provider={args.provider}")
    print(f"preset={args.preset}")
    print(f"terms={len(result.terms)} phrases={len(result.phrases)} warnings={len(result.quality_warnings)}")
    print(f"output={args.output}")
    print(f"raw={os.environ['RAW_MODEL_OUTPUT_PATH']}")


if __name__ == "__main__":
    asyncio.run(main())
