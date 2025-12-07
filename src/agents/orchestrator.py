import re
from src.llm.client import plan_tools, summarize_answer
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
    plan = plan_tools(provider, query)
    if not plan:
        name, version = _extract_pkg_spec(query)
        if name and version:
            plan = [{"tool": "osv.query", "args": {"name": name, "version": version}}]
    results = []
    for step in plan:
        t = step.get("tool")
        a = step.get("args") or {}
        if t == "osv.query":
            res = query_pypi_vulns(a.get("name"), a.get("version"))
            stats = summary_stats(res)
            fixes = first_fixed_versions(res)
            results.append({"tool": t, "args": a, "result": res, "stats": stats, "fixed": fixes})
        elif t == "pypi.info":
            info = project_info(a.get("name"))
            results.append({"tool": t, "args": a, "result": info})
        elif t == "scan.requirements" and requirements_path:
            scan = run_scan(requirements_path, python_version, out_dir)
            results.append({"tool": t, "args": {"path": requirements_path, "python_version": python_version}, "result": scan})
    answer_text = summarize_answer(provider, query, results, history)
    return {"query": query, "plan": plan, "results": results, "answer_text": answer_text}

def render_answer(query: str, results: list) -> dict:
    return {}
