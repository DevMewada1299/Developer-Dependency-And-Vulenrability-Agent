import os
import json
import requests

def _ollama_url() -> str:
    return os.environ.get("OLLAMA_BASE", "http://localhost:11434")

def _model_name(provider: str) -> str:
    if provider == "llama":
        return os.environ.get("LLAMA_MODEL", "llama3.1")
    if provider == "phi":
        return os.environ.get("PHI_MODEL", "phi3")
    raise ValueError("unsupported provider")

def model_info(provider: str) -> dict:
    return {"provider": provider, "model": _model_name(provider), "base": _ollama_url()}

def generate(provider: str, prompt: str) -> str:
    url = f"{_ollama_url()}/api/generate"
    model = _model_name(provider)
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("response") or ""

def plan_tools(provider: str, query: str) -> list:
    sys = (
        "You are a local dependency security assistant. "
        "Output only a compact JSON list of tool calls. "
        "Tools: osv.query{name,version}, pypi.info{name}, scan.requirements{path,python_version}. "
        "Prefer minimal calls."
    )
    tpl = (
        "System:\n" + sys + "\n\n" +
        "User:\n" + query + "\n\n" +
        "Return JSON only: [{\"tool\": \"osv.query\", \"args\": {\"name\": \"urllib3\", \"version\": \"1.25.8\"}}]"
    )
    try:
        out = generate(provider, tpl)
        j = json.loads(out)
        if isinstance(j, list):
            return j
        return []
    except Exception:
        return []

def summarize_answer(provider: str, query: str, results: list, history: list | None = None) -> str:
    sys = (
        "You synthesize dependency security tool results into clear developer advice. "
        "Always produce only the final answer text. Include actionable pins and pip commands. "
        "Prioritize safety, respect constraints, and reference CVE IDs when present."
    )
    payload = json.dumps({"query": query, "results": results, "history": history or []})
    tpl = "System:\n" + sys + "\n\n" + "User:\n" + payload + "\n\n" + "Answer:"
    try:
        return generate(provider, tpl)
    except Exception:
        return "LLM endpoint unavailable. Start local LLM and retry."
