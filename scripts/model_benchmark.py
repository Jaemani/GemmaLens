#!/usr/bin/env python3
import argparse
import asyncio
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.llm import get_model_adapter  # noqa: E402
from app.services.chunking_service import ChunkingService  # noqa: E402
from app.services.model_runtime_service import ModelRuntimeService  # noqa: E402


@dataclass(frozen=True)
class BenchmarkSample:
    sample_id: str
    title: str
    text: str


SAMPLES = [
    BenchmarkSample(
        sample_id="academic_sleep",
        title="Sleep and learning paper excerpt",
        text=(
            "Although previous studies have suggested a correlation between sleep deprivation "
            "and reduced cognitive performance, the extent to which these findings generalize "
            "across real-world learning environments remains unclear. To address this gap, "
            "we analyze longitudinal study logs collected from undergraduate students over a "
            "six-week period."
        ),
    ),
    BenchmarkSample(
        sample_id="technical_docs",
        title="Technical documentation excerpt",
        text=(
            "When the cache invalidation policy is configured incorrectly, stale metadata may "
            "propagate across worker nodes and cause downstream requests to resolve against "
            "outdated schema definitions. The migration runner therefore performs an idempotent "
            "preflight check before applying destructive operations."
        ),
    ),
    BenchmarkSample(
        sample_id="film_review",
        title="Film review excerpt",
        text=(
            "The film deliberately withholds exposition during the opening act, forcing viewers "
            "to infer the protagonist's motivation from fragmented dialogue and recurring visual "
            "motifs. This restraint makes the final confrontation feel less like a plot twist and "
            "more like the inevitable consequence of choices made long before the story began."
        ),
    ),
]


async def run_case(preset: str, sample: BenchmarkSample, output_dir: Path) -> dict[str, object]:
    provider = "mlx" if "mlx" in preset else "mock"
    raw_path = output_dir / "raw" / f"{preset}_{sample.sample_id}.txt"
    normalized_path = output_dir / "normalized" / f"{preset}_{sample.sample_id}.json"
    runtime_config = output_dir / "model_runtime_benchmark.json"

    os.environ["MODEL_PROVIDER"] = provider
    os.environ["MODEL_RUNTIME_CONFIG_PATH"] = str(runtime_config)
    os.environ["RAW_MODEL_OUTPUT_PATH"] = str(raw_path)
    get_settings.cache_clear()

    runtime_config.parent.mkdir(parents=True, exist_ok=True)
    runtime_config.write_text(json.dumps({"preset_id": preset, "provider": provider}, indent=2), encoding="utf-8")

    started = perf_counter()
    adapter = get_model_adapter()
    provider_config = ModelRuntimeService().provider_config()
    chunks = ChunkingService().chunk(sample.text)
    result = await adapter.analyze_document(sample.sample_id, sample.text, chunks)
    duration_s = round(perf_counter() - started, 2)

    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    raw_chars = raw_path.stat().st_size if raw_path.exists() else 0
    summary_complete = all(
        [
            bool(result.summaries.one_line.strip()),
            bool(result.summaries.simple.strip()),
            bool(result.summaries.academic.strip()),
        ]
    )
    return {
        "preset": preset,
        "sample_id": sample.sample_id,
        "title": sample.title,
        "duration_s": duration_s,
        "terms": len(result.terms),
        "phrases": len(result.phrases),
        "sentences": len(result.sentences),
        "study_notes": len(result.summaries.study_notes),
        "warnings": len(result.quality_warnings),
        "warning_codes": ",".join(result.quality_warnings),
        "summary_complete": summary_complete,
        "raw_chars": raw_chars,
        "mlx_model_path": str(provider_config.get("mlx_model_path", "")),
        "normalized_path": str(normalized_path.relative_to(ROOT)),
        "raw_path": str(raw_path.relative_to(ROOT)) if raw_path.exists() else "",
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local model presets on fixed language-learning samples.")
    parser.add_argument("--presets", nargs="+", default=["gemma4-e2b-mlx", "gemma4-e4b-mlx"])
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp" / "model_benchmark")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for preset in args.presets:
      for sample in SAMPLES:
          print(f"running preset={preset} sample={sample.sample_id}", flush=True)
          row = await run_case(preset, sample, args.output_dir)
          rows.append(row)
          print(
              f"done preset={preset} sample={sample.sample_id} duration={row['duration_s']}s "
              f"terms={row['terms']} phrases={row['phrases']} warnings={row['warnings']}",
              flush=True,
          )

    json_path = args.output_dir / "summary.json"
    csv_path = args.output_dir / "summary.csv"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"summary_json={json_path}")
    print(f"summary_csv={csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
