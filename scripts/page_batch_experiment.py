#!/usr/bin/env python3
"""Compare current section-by-section preparation with a page-batch design.

This is a structural experiment, not a full model benchmark. It uses the real
PDF extractor and section splitter, then estimates model-call pressure from
the actual number of pages and logical sections found in each paper.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.document_ingestion_service import DocumentIngestionService  # noqa: E402
from app.services.document_section_service import DocumentSectionService  # noqa: E402


@dataclass(frozen=True)
class PaperBatchMetrics:
    paper: str
    pdf_pages: int
    pages_with_learning_sections: int
    learning_sections: int
    pages_with_multiple_sections: int
    max_sections_on_one_page: int
    continued_sections: int
    current_http_requests: int
    proposed_page_batch_requests: int
    current_mlx_model_calls: int
    proposed_mlx_model_calls: int
    current_remote_q4_model_calls: int
    proposed_remote_q4_model_calls: int
    current_remote_full_model_calls: int
    proposed_remote_full_model_calls: int
    request_reduction_pct: float
    mlx_call_reduction_pct: float
    remote_q4_call_reduction_pct: float
    remote_full_call_reduction_pct: float


def _pct_reduction(current: int, proposed: int) -> float:
    if current <= 0:
        return 0.0
    return round((1 - proposed / current) * 100, 1)


def _pdf_page(label: str | None) -> int | None:
    match = re.match(r"PDF page (\d+)$", label or "")
    return int(match.group(1)) if match else None


def measure_paper(path: Path) -> PaperBatchMetrics:
    ingestion = DocumentIngestionService()
    splitter = DocumentSectionService()
    extracted = ingestion.normalize_text(ingestion._extract_pdf(path.read_bytes()))
    pdf_pages = len({int(match.group(1)) for match in re.finditer(r"\[\[GEMMALENS_PDF_PAGE:(\d+)]]", extracted)})
    sections = splitter.split_with_labels(extracted)

    by_page: dict[int, int] = defaultdict(int)
    unknown_page_sections = 0
    for section in sections:
        page = _pdf_page(section.source_label)
        if page is None:
            unknown_page_sections += 1
        else:
            by_page[page] += 1

    learning_sections = len(sections)
    page_batch_requests = len(by_page) + unknown_page_sections
    current_requests = learning_sections

    # Current local MLX/Ollama adapter: one model generation per section.
    # Current remote adapter: Q4 route skips meta/concepts generation but still
    # does terms, phrases, and sentences; full route does five atomic tasks.
    # Proposed page-batch design: one generation returns page section boundaries
    # plus per-section lessons for that page.
    current_mlx = learning_sections
    proposed_mlx = page_batch_requests
    current_remote_q4 = learning_sections * 3
    proposed_remote_q4 = page_batch_requests
    current_remote_full = learning_sections * 5
    proposed_remote_full = page_batch_requests

    return PaperBatchMetrics(
        paper=path.name,
        pdf_pages=pdf_pages,
        pages_with_learning_sections=len(by_page),
        learning_sections=learning_sections,
        pages_with_multiple_sections=sum(1 for count in by_page.values() if count > 1),
        max_sections_on_one_page=max(by_page.values(), default=0),
        continued_sections=sum(1 for section in sections if section.continuation),
        current_http_requests=current_requests,
        proposed_page_batch_requests=page_batch_requests,
        current_mlx_model_calls=current_mlx,
        proposed_mlx_model_calls=proposed_mlx,
        current_remote_q4_model_calls=current_remote_q4,
        proposed_remote_q4_model_calls=proposed_remote_q4,
        current_remote_full_model_calls=current_remote_full,
        proposed_remote_full_model_calls=proposed_remote_full,
        request_reduction_pct=_pct_reduction(current_requests, page_batch_requests),
        mlx_call_reduction_pct=_pct_reduction(current_mlx, proposed_mlx),
        remote_q4_call_reduction_pct=_pct_reduction(current_remote_q4, proposed_remote_q4),
        remote_full_call_reduction_pct=_pct_reduction(current_remote_full, proposed_remote_full),
    )


def render_markdown(rows: list[PaperBatchMetrics]) -> str:
    total = PaperBatchMetrics(
        paper="TOTAL",
        pdf_pages=sum(row.pdf_pages for row in rows),
        pages_with_learning_sections=sum(row.pages_with_learning_sections for row in rows),
        learning_sections=sum(row.learning_sections for row in rows),
        pages_with_multiple_sections=sum(row.pages_with_multiple_sections for row in rows),
        max_sections_on_one_page=max((row.max_sections_on_one_page for row in rows), default=0),
        continued_sections=sum(row.continued_sections for row in rows),
        current_http_requests=sum(row.current_http_requests for row in rows),
        proposed_page_batch_requests=sum(row.proposed_page_batch_requests for row in rows),
        current_mlx_model_calls=sum(row.current_mlx_model_calls for row in rows),
        proposed_mlx_model_calls=sum(row.proposed_mlx_model_calls for row in rows),
        current_remote_q4_model_calls=sum(row.current_remote_q4_model_calls for row in rows),
        proposed_remote_q4_model_calls=sum(row.proposed_remote_q4_model_calls for row in rows),
        current_remote_full_model_calls=sum(row.current_remote_full_model_calls for row in rows),
        proposed_remote_full_model_calls=sum(row.proposed_remote_full_model_calls for row in rows),
        request_reduction_pct=0.0,
        mlx_call_reduction_pct=0.0,
        remote_q4_call_reduction_pct=0.0,
        remote_full_call_reduction_pct=0.0,
    )
    total = PaperBatchMetrics(
        **{
            **asdict(total),
            "request_reduction_pct": _pct_reduction(total.current_http_requests, total.proposed_page_batch_requests),
            "mlx_call_reduction_pct": _pct_reduction(total.current_mlx_model_calls, total.proposed_mlx_model_calls),
            "remote_q4_call_reduction_pct": _pct_reduction(total.current_remote_q4_model_calls, total.proposed_remote_q4_model_calls),
            "remote_full_call_reduction_pct": _pct_reduction(total.current_remote_full_model_calls, total.proposed_remote_full_model_calls),
        }
    )
    all_rows = [*rows, total]

    lines = [
        "# Page-Batch Analysis Experiment",
        "",
        "This report compares the current section-by-section preparation flow with a proposed page-batch flow using real PDF extraction and section splitting.",
        "",
        "## Method",
        "",
        "- Input: real PDFs from `tmp/eval_papers`.",
        "- Current flow: one frontend/backend analysis request per logical section.",
        "- Proposed flow: one request per PDF page with learning text; the model returns page-local section boundaries plus lessons.",
        "- Local MLX/Ollama estimate: one generation per request.",
        "- Remote Q4 estimate: current route performs three atomic generations per section; page-batch target performs one generation per page.",
        "- Remote full estimate: current route performs five atomic generations per section; page-batch target performs one generation per page.",
        "",
        "## Results",
        "",
        "| Paper | PDF pages | Learning pages | Sections | Current requests | Page-batch requests | Request reduction | Current Q4 calls | Page-batch calls | Q4 call reduction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in all_rows:
        lines.append(
            f"| {row.paper} | {row.pdf_pages} | {row.pages_with_learning_sections} | {row.learning_sections} | "
            f"{row.current_http_requests} | {row.proposed_page_batch_requests} | {row.request_reduction_pct}% | "
            f"{row.current_remote_q4_model_calls} | {row.proposed_remote_q4_model_calls} | {row.remote_q4_call_reduction_pct}% |"
        )

    lines.extend(
        [
            "",
            "## Boundary Findings",
            "",
            "| Paper | Pages with multiple sections | Max sections on one page | Continued sections |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(f"| {row.paper} | {row.pages_with_multiple_sections} | {row.max_sections_on_one_page} | {row.continued_sections} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The current section-by-section pipeline is accurate enough to keep lessons source-grounded, but it multiplies model startup, HTTP, JSON, and database overhead by the number of sections. A page-batch design keeps the learner-facing page model while still producing section-level lessons.",
            "",
            "The page-batch approach should be implemented as an experimental backend endpoint before replacing the current section endpoint. It needs explicit handling for sections that continue across page boundaries and for pages dominated by references, tables, or equations.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure request/model-call pressure for page-batch analysis.")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "tmp" / "eval_papers")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp" / "page_batch_experiment")
    args = parser.parse_args()

    papers = sorted(path for path in args.input_dir.glob("*.pdf"))
    if not papers:
        raise SystemExit(f"No PDFs found in {args.input_dir}")

    rows = [measure_paper(path) for path in papers]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps([asdict(row) for row in rows], indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(render_markdown(rows), encoding="utf-8")
    print((args.output_dir / "summary.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
