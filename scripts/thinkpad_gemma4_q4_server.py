#!/usr/bin/env python3
"""Gemma 4 Q4 GGUF wrapper around llama-server for ThinkPad testing."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

LLAMA_SERVER = os.environ.get("LLAMA_SERVER", "/home/jaeman/Models/llama/bin/llama-server")
MODEL_PATH = os.environ.get("GEMMA4_Q4_MODEL", "/home/jaeman/Models/llama/q4/gemma-4-E2B-it.Q4_K_M.gguf")
LLAMA_HOST = os.environ.get("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.environ.get("LLAMA_PORT", "11446"))
CTX_SIZE = os.environ.get("LLAMA_CTX_SIZE", "4096")
THREADS = os.environ.get("LLAMA_THREADS", "8")
BATCH = os.environ.get("LLAMA_BATCH", "256")
UBATCH = os.environ.get("LLAMA_UBATCH", "128")

llama_proc: subprocess.Popen[bytes] | None = None
started_at: float | None = None


def llama_url(path: str) -> str:
    return f"http://{LLAMA_HOST}:{LLAMA_PORT}{path}"


def start_llama() -> None:
    global llama_proc, started_at
    if llama_proc and llama_proc.poll() is None:
        return
    model = Path(MODEL_PATH)
    if not model.exists():
        raise FileNotFoundError(f"Missing model: {model}")
    cmd = [
        LLAMA_SERVER,
        "-m",
        str(model),
        "--host",
        LLAMA_HOST,
        "--port",
        str(LLAMA_PORT),
        "-c",
        CTX_SIZE,
        "-t",
        THREADS,
        "-b",
        BATCH,
        "-ub",
        UBATCH,
        "--no-webui",
        "--reasoning",
        "off",
    ]
    llama_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    started_at = time.time()
    deadline = time.time() + 120
    last_error: Exception | None = None
    while time.time() < deadline:
        if llama_proc.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {llama_proc.returncode}")
        try:
            urllib.request.urlopen(llama_url("/health"), timeout=2).read()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise TimeoutError(f"llama-server did not become ready: {last_error}")


def stop_llama() -> None:
    global llama_proc
    if llama_proc and llama_proc.poll() is None:
        llama_proc.send_signal(signal.SIGTERM)
        try:
            llama_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            llama_proc.kill()
    llama_proc = None


@app.route("/health", methods=["GET", "POST"])
def health():
    loaded = bool(llama_proc and llama_proc.poll() is None)
    return jsonify(
        {
            "status": "healthy" if loaded else "starting",
            "active_model": "e2b-q4" if loaded else None,
            "available_models": ["e2b-q4"],
            "backend": "llama.cpp",
            "quantization": "Q4_K_M",
            "uptime_seconds": round(time.time() - started_at, 1) if started_at else 0,
        }
    )


@app.route("/models/status", methods=["GET"])
def models_status():
    loaded = bool(llama_proc and llama_proc.poll() is None)
    return jsonify(
        {
            "e2b-q4": {
                "name": "gemma-4-E2B-it.Q4_K_M.gguf",
                "path": MODEL_PATH,
                "loaded": loaded,
                "active": loaded,
                "runtime": "llama.cpp",
            }
        }
    )


@app.route("/generate", methods=["POST"])
def generate():
    data: dict[str, Any] = request.get_json() or {}
    prompt = str(data.get("prompt", ""))
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400
    max_tokens = int(data.get("max_tokens", 256))
    temperature = float(data.get("temperature", 0.1))
    json_mode = bool(data.get("json_mode", False))
    if json_mode:
        prompt = f"{prompt}\n\nRespond with ONLY valid JSON, no markdown."
    start = time.time()
    try:
        payload = json.dumps(
            {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_format": {"type": "json_object"} if json_mode else None,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            llama_url("/v1/chat/completions"),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=max(120, max_tokens * 20)) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    elapsed = time.time() - start
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    usage = body.get("usage", {}) if isinstance(body.get("usage"), dict) else {}
    timings = body.get("timings", {}) if isinstance(body.get("timings"), dict) else {}
    text = str(message.get("content") or message.get("reasoning_content") or "")
    output_tokens = usage.get("completion_tokens", timings.get("predicted_n", 0)) or 0
    input_tokens = usage.get("prompt_tokens", timings.get("prompt_n", 0)) or 0
    return jsonify(
        {
            "text": text,
            "model": "e2b-q4",
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens if isinstance(input_tokens, int) and isinstance(output_tokens, int) else None,
            },
            "timing": {
                "generation_time": round(elapsed, 2),
                "tokens_per_second": round((output_tokens / elapsed), 2) if output_tokens and elapsed > 0 else 0,
            },
            "backend": "llama.cpp",
            "quantization": "Q4_K_M",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=11445)
    parser.add_argument("--no-preload", action="store_true")
    args = parser.parse_args()
    if not args.no_preload:
        start_llama()
    app.run(host=args.host, port=args.port, threaded=True)
