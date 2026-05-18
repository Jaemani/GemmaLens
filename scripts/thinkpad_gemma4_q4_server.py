#!/usr/bin/env python3
"""Gemma 4 GGUF wrapper around llama-server for local or edge testing."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEFAULT_LLAMA_SERVER = "/opt/homebrew/bin/llama-server"
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", DEFAULT_LLAMA_SERVER)
MODEL_ALIASES = {
    "e2b-q4": os.environ.get("GEMMA4_E2B_GGUF", "~/Models/gemma4-25.8B/gemma4-25.8B-Q4_K_M.gguf"),
    "gemma4-26b-gguf": os.environ.get("GEMMA4_26B_GGUF", "~/Models/gemma4-25.8B/gemma4-25.8B-Q4_K_M.gguf"),
    "26b": os.environ.get("GEMMA4_26B_GGUF", "~/Models/gemma4-25.8B/gemma4-25.8B-Q4_K_M.gguf"),
    "gemma4-31b-gguf": os.environ.get("GEMMA4_31B_GGUF", "~/Models/gemma4-31.3b/gemma4-31.3B-Q4_K_M.gguf"),
    "31b": os.environ.get("GEMMA4_31B_GGUF", "~/Models/gemma4-31.3b/gemma4-31.3B-Q4_K_M.gguf"),
}
DEFAULT_MODEL = os.environ.get("GEMMA4_GGUF_DEFAULT_MODEL", "gemma4-26b-gguf")
LLAMA_HOST = os.environ.get("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.environ.get("LLAMA_PORT", "11446"))
CTX_SIZE = os.environ.get("LLAMA_CTX_SIZE", "4096")
THREADS = os.environ.get("LLAMA_THREADS", "8")
BATCH = os.environ.get("LLAMA_BATCH", "256")
UBATCH = os.environ.get("LLAMA_UBATCH", "128")

llama_proc: subprocess.Popen[bytes] | None = None
started_at: float | None = None
active_model: str | None = None


def llama_url(path: str) -> str:
    return f"http://{LLAMA_HOST}:{LLAMA_PORT}{path}"


def model_path_for(model_name: str | None) -> Path:
    key = (model_name or DEFAULT_MODEL).strip().lower()
    raw_path = MODEL_ALIASES.get(key) or MODEL_ALIASES.get(DEFAULT_MODEL) or next(iter(MODEL_ALIASES.values()))
    return Path(raw_path).expanduser()


def start_llama(model_name: str | None = None) -> None:
    global llama_proc, started_at, active_model
    requested = (model_name or DEFAULT_MODEL).strip().lower()
    if llama_proc and llama_proc.poll() is None and active_model == requested:
        return
    if llama_proc and llama_proc.poll() is None:
        stop_llama()
    model = model_path_for(requested)
    if not Path(LLAMA_SERVER).exists():
        raise FileNotFoundError(f"Missing llama-server: {LLAMA_SERVER}")
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
    active_model = requested
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
    global llama_proc, active_model
    if llama_proc and llama_proc.poll() is None:
        llama_proc.send_signal(signal.SIGTERM)
        try:
            llama_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            llama_proc.kill()
    llama_proc = None
    active_model = None


def health_payload() -> dict[str, Any]:
    loaded = bool(llama_proc and llama_proc.poll() is None)
    return {
        "status": "healthy" if loaded else "starting",
        "active_model": active_model if loaded else None,
        "available_models": list(MODEL_ALIASES.keys()),
        "backend": "llama.cpp",
        "quantization": "Q4_K_M",
        "uptime_seconds": round(time.time() - started_at, 1) if started_at else 0,
    }


def models_status_payload() -> dict[str, Any]:
    loaded = bool(llama_proc and llama_proc.poll() is None)
    return {
        model_name: {
            "name": Path(path).expanduser().name,
            "path": str(Path(path).expanduser()),
            "loaded": loaded and active_model == model_name,
            "active": loaded and active_model == model_name,
            "runtime": "llama.cpp",
        }
        for model_name, path in MODEL_ALIASES.items()
    }


def generate_payload(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    prompt = str(data.get("prompt", ""))
    if not prompt:
        return {"error": "Missing prompt"}, 400
    max_tokens = int(data.get("max_tokens", 256))
    model_name = str(data.get("model") or DEFAULT_MODEL).strip().lower()
    temperature = float(data.get("temperature", 0.1))
    json_mode = bool(data.get("json_mode", False))
    if json_mode:
        prompt = f"{prompt}\n\nRespond with ONLY valid JSON, no markdown."
    start = time.time()
    try:
        start_llama(model_name)
        request_body = json.dumps(
            {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_format": {"type": "json_object"} if json_mode else None,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            llama_url("/v1/chat/completions"),
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=max(120, max_tokens * 20)) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}, 500

    elapsed = time.time() - start
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    usage = body.get("usage", {}) if isinstance(body.get("usage"), dict) else {}
    timings = body.get("timings", {}) if isinstance(body.get("timings"), dict) else {}
    text = str(message.get("content") or message.get("reasoning_content") or "")
    output_tokens = usage.get("completion_tokens", timings.get("predicted_n", 0)) or 0
    input_tokens = usage.get("prompt_tokens", timings.get("prompt_n", 0)) or 0
    return {
        "text": text,
        "model": active_model or model_name,
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
    }, 200


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(health_payload())
            return
        if self.path == "/models/status":
            self._write_json(models_status_payload())
            return
        self._write_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/health":
            self._write_json(health_payload())
            return
        if self.path != "/generate":
            self._write_json({"error": "Not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._write_json({"error": "Invalid JSON"}, 400)
            return
        payload, status = generate_payload(body)
        self._write_json(payload, status)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=11445)
    parser.add_argument("--no-preload", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    if not args.no_preload:
        start_llama(args.model)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    finally:
        stop_llama()
