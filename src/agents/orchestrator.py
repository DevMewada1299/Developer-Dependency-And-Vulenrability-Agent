import re
import time
import json
import src.llm.client as llm_client
from src.storage.db import init_db, record_session
from src.tools.osv_client import query_pypi_vulns, summary_stats, first_fixed_versions
from src.tools.pypi_client import project_info
from src.agents.dependency_agent import run_scan
from src.tools.security import run_pip_audit, summarize_pip_audit
from src.security.guardrails import check_query

def _extract_pkg_spec(query: str) -> tuple[str | None, str | None]:
    m = re.search(r"([A-Za-z0-9_\-]+)\s*==\s*([0-9a-zA-Z\._\-]+)", query)
    if m:
        name = m.group(1)
        version = m.group(2)
        if name.lower() == "python":
            return None, None
        return name, version
    m = re.search(r"([A-Za-z0-9_\-]+)\s*=\s*([0-9a-zA-Z\._\-]+)", query)
    if m:
        name = m.group(1)
        version = m.group(2)
        if name.lower() == "python":
            return None, None
        return name, version
    m = re.search(r"([A-Za-z0-9_\-]+)\s+([0-9][0-9a-zA-Z\._\-]*)", query)
    if m:
        name = m.group(1)
        version = m.group(2)
        if name.lower() == "python":
            return None, None
        return name, version
    return None, None

def advise(query: str, provider: str, requirements_path: str | None = None, python_version: str = "3.11", out_dir: str = "data", history: list | None = None, prompt_style: str = "compact_json", planning_mode: str = "single", verify: bool = False) -> dict:
    gr = check_query(query)
    if gr.get("blocked"):
        meta = {"provider": provider, "model": llm_client.model_info(provider), "tool_calls": [], "prompt_style": prompt_style, "planning_mode": planning_mode, "verify_ms": 0, "guardrails_blocked": True, "guardrails_matches": gr.get("matches")}
        try:
            init_db()
            record_session(meta=meta, plan=[], results=[], answer_text="SECURITY ALERT: This query violates safety protocols.")
        except Exception:
            pass
        return {"query": query, "plan": [], "results": [], "answer_text": "SECURITY ALERT: This query violates safety protocols.", "meta": meta}
    if not gr.get("in_scope"):
        meta = {"provider": provider, "model": llm_client.model_info(provider), "tool_calls": [], "prompt_style": prompt_style, "planning_mode": planning_mode, "verify_ms": 0, "guardrails_blocked": False, "guardrails_matches": [], "guardrails_scope": False}
        try:
            init_db()
            record_session(meta=meta, plan=[], results=[], answer_text="OUT OF SCOPE: Ask about dependency security (requirements, pins, OSV/PyPI, audit).")
        except Exception:
            pass
        return {"query": query, "plan": [], "results": [], "answer_text": "OUT OF SCOPE: Ask about dependency security (requirements, pins, OSV/PyPI, audit).", "meta": meta}
    llm_meta = {"provider": provider, "model": llm_client.model_info(provider)}
    t0 = time.time()
    if planning_mode.startswith("consensus"):
        try:
            n = int(planning_mode.split("-")[1])
        except Exception:
            n = 3
        plan = llm_client.plan_tools_consensus(provider, query, style=prompt_style, n=n)
    else:
        plan = llm_client.plan_tools(provider, query, style=prompt_style)
    t1 = time.time()
    if not plan:
        # Prefer requirements scanning when a file is provided
        if requirements_path:
            plan = [{"tool": "scan.requirements", "args": {"path": requirements_path, "python_version": python_version}}]
        else:
            name, version = _extract_pkg_spec(query)
            if name and version:
                plan = [{"tool": "osv.query", "args": {"name": name, "version": version}}]
    # Ensure requirements scanning runs when a file is provided
    if requirements_path:
        has_scan = any(step.get("tool") == "scan.requirements" for step in plan)
        if not has_scan:
            plan.insert(0, {"tool": "scan.requirements", "args": {"path": requirements_path, "python_version": python_version}})
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
        elif t == "security.audit" and requirements_path:
            ts = time.time()
            data = run_pip_audit(requirements_path)
            summ = summarize_pip_audit(data)
            results.append({"tool": t, "args": {"path": requirements_path}, "result": data, "summary": summ})
            te = time.time()
            tool_calls_meta.append({"tool": t, "args": {"path": requirements_path}, "duration_ms": int((te - ts) * 1000), "audit_summary": summ})
    t2 = time.time()
    answer_text, summ_cache_hit = llm_client.summarize_answer(provider, query, results, history, style=prompt_style, use_cache=True)
    verify_ms = 0
    if verify:
        tv0 = time.time()
        answer_text, verify_cache_hit = llm_client.verify_answer(provider, query, results, answer_text, style=prompt_style, use_cache=True)
        tv1 = time.time()
        verify_ms = int((tv1 - tv0) * 1000)
    t3 = time.time()
    meta = {
        "provider": provider,
        "model": llm_meta.get("model"),
        "llm": {"plan_ms": int((t1 - t0) * 1000), "summarize_ms": int((t3 - t2) * 1000)},
        "tool_calls": tool_calls_meta,
        "prompt_style": prompt_style,
        "planning_mode": planning_mode,
        "verify_ms": verify_ms,
        "summ_cache_hit": summ_cache_hit,
        "verify_cache_hit": verify_cache_hit if verify else False,
        "guardrails_blocked": False,
        "guardrails_matches": [],
        "guardrails_scope": True,
    }
    try:
        init_db()
        record_session(meta=meta, plan=plan, results=results, answer_text=answer_text)
    except Exception:
        pass
    return {"query": query, "plan": plan, "results": results, "answer_text": answer_text, "meta": meta}

def render_answer(query: str, results: list) -> dict:
    return {}
