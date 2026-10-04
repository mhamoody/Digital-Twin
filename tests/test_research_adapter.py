import json
import httpx
import pytest
from digital_twin.evaluation.research_adapter import ResearchModelAdapter, ResearchModelError, EXPECTED_DIGEST

def transport(routes):
    def handler(request):
        return routes(request)
    return httpx.MockTransport(handler)

def tags():
    return {"models":[{"name":"qwen2.5:7b","digest":EXPECTED_DIGEST,"details":{"family":"qwen2","parameter_size":"7.6B","quantization_level":"Q4_K_M"}}]}

def test_metadata_and_readiness():
    def route(r):
        assert r.url.path == "/api/tags"
        return httpx.Response(200,json=tags())
    a=ResearchModelAdapter(endpoint="http://127.0.0.1:11434",model_name="qwen2.5:7b",transport=transport(route))
    out=a.readiness()
    assert out["status"]=="ready" and out["digest"]==EXPECTED_DIGEST
    assert out["quantization"]=="Q4_K_M"

def test_digest_mismatch_rejected():
    def route(r): return httpx.Response(200,json={"models":[{"name":"qwen2.5:7b","digest":"wrong"}]})
    a=ResearchModelAdapter(endpoint="http://127.0.0.1:11434",model_name="qwen2.5:7b",transport=transport(route))
    with pytest.raises(ResearchModelError,match="MODEL_DIGEST_MISMATCH"): a.metadata()

def test_generation_request_and_metadata():
    def route(r):
        if r.url.path=="/api/tags": return httpx.Response(200,json=tags())
        body=json.loads(r.content)
        assert body["model"]=="qwen2.5:7b"
        assert body["options"]=={"temperature":0.0,"seed":42,"num_predict":1200,"num_ctx":8192}
        assert "top_p" not in body["options"]
        assert body["keep_alive"] == "10m"
        return httpx.Response(200,json={"model":"qwen2.5:7b","response":"{\"accepted\":true}"})
    a=ResearchModelAdapter(endpoint="http://127.0.0.1:11434",model_name="qwen2.5:7b",transport=transport(route))
    out=a.generate({"case_id":"x"},schema={"type":"object"})
    assert out["parsed"]["accepted"] is True and out["metadata"]["model_name"]=="qwen2.5:7b"

def test_invalid_json_and_no_fallback():
    def route(r):
        if r.url.path=="/api/tags": return httpx.Response(200,json=tags())
        return httpx.Response(200,json={"model":"qwen2.5:7b","response":"not-json"})
    a=ResearchModelAdapter(endpoint="http://127.0.0.1:11434",model_name="qwen2.5:7b",transport=transport(route))
    with pytest.raises(ResearchModelError,match="MODEL_JSON_INVALID"): a.generate({})

def test_unavailable_and_endpoint_rejection():
    def route(r): raise httpx.ConnectError("offline")
    a=ResearchModelAdapter(endpoint="http://127.0.0.1:11434",model_name="qwen2.5:7b",transport=transport(route))
    assert a.readiness()["error_code"]=="MODEL_UNAVAILABLE"
    with pytest.raises(ResearchModelError,match="MODEL_ENDPOINT_INVALID"):
        ResearchModelAdapter(endpoint="https://remote.example",model_name="qwen2.5:7b")

