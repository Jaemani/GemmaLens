#!/usr/bin/env python3
"""Small monitor for the Gemma 4 HTTP server used by GemmaLens."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any


def request_json(url: str, *, payload: dict[str, Any] | None = None, timeout: float = 20) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_status(base_url: str, timeout: float) -> str:
    health = request_json(f"{base_url}/health", timeout=timeout)
    line = f"health={health.get('status', '?')} active={health.get('active_model', '?')}"
    available = health.get("available_models")
    if isinstance(available, list):
        line += f" available={','.join(str(model) for model in available)}"
    try:
        status = request_json(f"{base_url}/models/status", timeout=timeout)
    except Exception:
        return line
    loaded = []
    for name, info in status.items():
        if isinstance(info, dict):
            flags = []
            if info.get("active"):
                flags.append("active")
            if info.get("loaded"):
                flags.append("loaded")
            loaded.append(f"{name}({','.join(flags) or 'idle'})")
    return f"{line} models={' '.join(loaded)}"


def run_probe(base_url: str, model: str, prompt: str, max_tokens: int, timeout: float) -> str:
    start = time.perf_counter()
    body = request_json(
        f"{base_url}/generate",
        payload={"prompt": prompt, "model": model, "max_tokens": max_tokens},
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    timing = body.get("timing", {}) if isinstance(body.get("timing"), dict) else {}
    tokens = body.get("tokens", {}) if isinstance(body.get("tokens"), dict) else {}
    text = str(body.get("text", "")).replace("\n", " ").strip()
    if len(text) > 100:
        text = f"{text[:97]}..."
    return (
        f"probe_model={body.get('model', model)} wall={elapsed:.2f}s "
        f"gen={float(timing.get('generation_time', 0)):.2f}s "
        f"tps={float(timing.get('tokens_per_second', 0)):.2f} "
        f"tokens=in:{tokens.get('input', '?')} out:{tokens.get('output', '?')} total:{tokens.get('total', '?')} "
        f"text={text!r}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor Gemma 4 server health, active model, and simple I/O speed.")
    parser.add_argument("--base-url", default="http://PRIVATE-GEMMA-SERVER:11444")
    parser.add_argument("--model", default="e2b", choices=["e2b", "e4b"])
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--probe", action="store_true", help="Send a tiny generate request each interval.")
    parser.add_argument("--once", action="store_true", help="Print one sample and exit.")
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--prompt", default="Say OK and one short reason.")
    args = parser.parse_args()

    while True:
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            parts = [timestamp, summarize_status(args.base_url.rstrip("/"), args.timeout)]
            if args.probe:
                parts.append(run_probe(args.base_url.rstrip("/"), args.model, args.prompt, args.max_tokens, args.timeout))
            print(" | ".join(parts), flush=True)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"{timestamp} | error={type(exc).__name__}: {exc}", flush=True)
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
