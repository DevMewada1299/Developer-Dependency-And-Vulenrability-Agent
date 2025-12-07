import os
import json
import requests
import time

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

def _plan_prompt(provider: str, query: str, style: str) -> str:
    if style == "react_json":
        sys = "You plan tool usage with ReAct. Think internally. Return only JSON tool calls."
    elif style == "deliberate_json":
        sys = "Deliberate step-by-step internally, then return only JSON tool calls."
    elif style == "strict_schema":
        sys = "Return only JSON conforming to [{tool: string, args: object}] with keys present."
    else:
        sys = "Return only a compact JSON list of tool calls."
    tools = "Tools: osv.query{name,version}, pypi.info{name}, scan.requirements{path,python_version}."
    return "System:\n" + sys + " " + tools + "\n\n" + "User:\n" + query + "\n\n" + "JSON:"

def plan_tools(provider: str, query: str, style: str = "compact_json") -> list:
    tpl = _plan_prompt(provider, query, style)
    try:
        out = generate(provider, tpl)
        j = json.loads(out)
        if isinstance(j, list):
            return j
        return []
    except Exception:
        return []

def _summ_prompt(provider: str, payload: str, style: str) -> str:
    if style == "react_json":
        sys = "Reason internally. Output only final answer text with pins and pip commands."
    elif style == "deliberate_json":
        sys = "Deliberate internally. Output only final answer text with pins and pip commands."
    elif style == "strict_schema":
        sys = "Output only final answer text."
    else:
        sys = "Output only final answer text with actionable pins and pip commands."
    return "System:\n" + sys + "\n\n" + "User:\n" + payload + "\n\n" + "Answer:"

def summarize_answer(provider: str, query: str, results: list, history: list | None = None, style: str = "compact_json") -> str:
    payload = json.dumps({"query": query, "results": results, "history": history or []})
    tpl = _summ_prompt(provider, payload, style)
    try:
        return generate(provider, tpl)
    except Exception:
        return "LLM endpoint unavailable. Start local LLM and retry."

def verify_answer(provider: str, query: str, results: list, draft: str, style: str = "compact_json") -> str:
    payload = json.dumps({"query": query, "results": results, "draft": draft})
    if style == "deliberate_json":
        sys = "Verify and correct. Output only improved final answer text."
    else:
        sys = "Verify and correct. Output only final answer text."
    tpl = "System:\n" + sys + "\n\n" + "User:\n" + payload + "\n\n" + "Answer:"
    try:
        return generate(provider, tpl)
    except Exception:
        return draft

def plan_tools_consensus(provider: str, query: str, style: str = "compact_json", n: int = 3, select: str = "min_calls") -> list:
    plans = []
    for _ in range(max(1, n)):
        p = plan_tools(provider, query, style=style)
        if isinstance(p, list) and p:
            plans.append(p)
    if not plans:
        return []
    if select == "min_calls":
        best = sorted(plans, key=lambda x: len(x))[0]
    else:
        best = plans[0]
    return best
