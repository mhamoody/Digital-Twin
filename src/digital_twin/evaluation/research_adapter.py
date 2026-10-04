from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


EXPECTED_DIGEST = "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"


class ResearchModelError(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class ResearchRuntime:
    endpoint: str | None
    model_name: str | None
    generation: dict[str, Any]


class ResearchModelAdapter:
    """Evaluation-only Ollama adapter; never used by operational prediction."""

    def __init__(self, endpoint=None, model_name=None, generation=None, *, transport=None, expected_digest=EXPECTED_DIGEST, timeout=300.0):
        self.runtime = ResearchRuntime(
            endpoint or os.getenv("DIGITAL_TWIN_RESEARCH_MODEL_URL"),
            model_name or os.getenv("DIGITAL_TWIN_RESEARCH_MODEL_NAME"),
            generation or {"temperature": 0.0, "seed": 42, "num_ctx": 8192, "num_predict": 1200},
        )
        self.transport = transport
        self.expected_digest = expected_digest
        self.timeout = timeout
        if self.runtime.endpoint:
            parsed = httpx.URL(self.runtime.endpoint)
            if parsed.scheme != "http" or parsed.host not in {"127.0.0.1", "localhost"} or parsed.path not in {"", "/"}:
                raise ResearchModelError("MODEL_ENDPOINT_INVALID")

    def _request(self, method: str, path: str, **kwargs):
        try:
            with httpx.Client(base_url=self.runtime.endpoint, transport=self.transport, timeout=self.timeout, trust_env=False) as client:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise ResearchModelError("MODEL_TIMEOUT") from exc
        except httpx.HTTPStatusError as exc:
            raise ResearchModelError("MODEL_HTTP_ERROR") from exc
        except httpx.RequestError as exc:
            raise ResearchModelError("MODEL_UNAVAILABLE") from exc
        except (ValueError, TypeError) as exc:
            raise ResearchModelError("MODEL_RESPONSE_INVALID") from exc
        if not isinstance(body, dict) or body.get("error"):
            raise ResearchModelError("MODEL_RESPONSE_INVALID")
        return body

    def metadata(self) -> dict[str, Any]:
        if not self.runtime.endpoint or not self.runtime.model_name:
            raise ResearchModelError("MODEL_CONFIGURATION_MISSING")
        body = self._request("GET", "/api/tags", timeout=5)
        models = body.get("models")
        if not isinstance(models, list):
            raise ResearchModelError("MODEL_RESPONSE_INVALID")
        item = next((m for m in models if isinstance(m, dict) and self.runtime.model_name in {m.get("name"), m.get("model")}), None)
        if item is None:
            raise ResearchModelError("MODEL_NOT_INSTALLED")
        digest = item.get("digest")
        if not isinstance(digest, str):
            raise ResearchModelError("MODEL_DIGEST_MISSING")
        if self.expected_digest and digest != self.expected_digest:
            raise ResearchModelError("MODEL_DIGEST_MISMATCH")
        return {"model_name": item.get("name") or item.get("model"), "digest": digest, "family": item.get("details", {}).get("family"), "parameter_size": item.get("details", {}).get("parameter_size"), "quantization": item.get("details", {}).get("quantization_level"), "runtime": "ollama", "endpoint": self.runtime.endpoint, "generation": dict(self.runtime.generation)}

    def readiness(self, *, verify_generation=False) -> dict[str, Any]:
        try:
            meta = self.metadata()
            if verify_generation:
                self.generate({"smoke": True}, system="Return JSON.", prompt="{}", schema={"type": "object"}, _smoke=True)
            return {"status": "ready", "inference_verified": bool(verify_generation), **meta}
        except ResearchModelError as exc:
            return {"status": "unavailable", "inference_verified": False, "error_code": exc.code, "model_name": self.runtime.model_name, "runtime": "ollama", "endpoint": self.runtime.endpoint}

    def generate(self, case, *, system="", prompt=None, schema=None, _smoke=False) -> dict[str, Any]:
        if not self.runtime.endpoint or not self.runtime.model_name:
            raise RuntimeError("BLOCKED BY MODEL ACCESS")
        meta = self.metadata()
        started = time.perf_counter()
        payload = {"model": self.runtime.model_name, "system": system, "prompt": prompt if prompt is not None else json.dumps(case, sort_keys=True), "stream": False, "keep_alive": "10m", "options": dict(self.runtime.generation)}
        if schema is not None:
            payload["format"] = schema
        body = self._request("POST", "/api/generate", json=payload)
        raw = body.get("response")
        if not isinstance(raw, str) or not raw.strip():
            raise ResearchModelError("MODEL_RESPONSE_INVALID")
        if body.get("model") not in (None, self.runtime.model_name):
            raise ResearchModelError("MODEL_IDENTITY_MISMATCH")
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ResearchModelError("MODEL_JSON_INVALID") from exc
        meta = {**meta, "latency_ms": round((time.perf_counter() - started) * 1000, 3), "output_hash": hashlib.sha256(raw.encode()).hexdigest()}
        return {"raw": raw, "parsed": parsed, "metadata": meta, "smoke": _smoke}



