import re
import time
import src.llm.client as llm_client
from src.tools.osv_client import query_pypi_vulns, summary_stats, first_fixed_versions
from src.tools.pypi_client import project_info
from src.agents.dependency_agent import run_scan

def _extract_pkg_spec(query: str) -> tuple[str | None, str | None]:
    m = re.search(r"([A-Za-z0-9_\-]+)\s*==\s*([0-9a-zA-Z\._\-]+)", query)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"([A-Za-z0-9_\-]+)\s*=\s*([0-9a-zA-Z\._\-]+)", query)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"([A-Za-z0-9_\-]+)\s+([0-9][0-9a-zA-Z\._\-]*)", query)
    if m:
        return m.group(1), m.group(2)
    return None, None

def advise(query: str, provider: str, requirements_path: str | None = None, python_version: str = "3.11", out_dir: str = "data", history: list | None = None) -> dict:
    llm_meta = {"provider": provider, "model": llm_client.model_info(provider)}
    t0 = time.time()
    plan = llm_client.plan_tools(provider, query)
    t1 = time.time()
    if not plan:
        name, version = _extract_pkg_spec(query)
        if name and version:
            plan = [{"tool": "osv.query", "args": {"name": name, "version": version}}]
    results = []
    tool_calls_meta = []
    for step in plan:
        t = step.get("tool")
        a = step.get("args") or {}
        if t == "osv.query":
            ts = time.time()
            res = query_pypi_vulns(a.get("name"), a.get("version"))
            stats = summary_stats(res)
            fixes = first_fixed_versions(res)
            results.append({"tool": t, "args": a, "result": res, "stats": stats, "fixed": fixes})
            te = time.time()
            tool_calls_meta.append({"tool": t, "args": a, "duration_ms": int((te - ts) * 1000), "stats": stats, "fixed": fixes})
        elif t == "pypi.info":
            ts = time.time()
            info = project_info(a.get("name"))
            results.append({"tool": t, "args": a, "result": info})
            te = time.time()
            releases_count = len((info or {}).get("releases") or {})
            tool_calls_meta.append({"tool": t, "args": a, "duration_ms": int((te - ts) * 1000), "releases_count": releases_count})
        elif t == "scan.requirements" and requirements_path:
            ts = time.time()
            scan = run_scan(requirements_path, python_version, out_dir)
            results.append({"tool": t, "args": {"path": requirements_path, "python_version": python_version}, "result": scan})
            te = time.time()
            tool_calls_meta.append({"tool": t, "args": {"path": requirements_path, "python_version": python_version}, "duration_ms": int((te - ts) * 1000), "packages_count": (scan or {}).get("count")})
    t2 = time.time()
    answer_text = llm_client.summarize_answer(provider, query, results, history)
    t3 = time.time()
    meta = {
        "provider": provider,
        "model": llm_meta.get("model"),
        "llm": {"plan_ms": int((t1 - t0) * 1000), "summarize_ms": int((t3 - t2) * 1000)},
        "tool_calls": tool_calls_meta,
    }
    return {"query": query, "plan": plan, "results": results, "answer_text": answer_text, "meta": meta}

def render_answer(query: str, results: list) -> dict:
    return {}
