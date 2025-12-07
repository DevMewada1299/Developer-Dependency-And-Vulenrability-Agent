import json
from pathlib import Path
from src.tools.osv_client import query_pypi_vulns, summary_stats
from src.tools.pypi_client import project_info, releases, requires_python_for_release
from src.util.versions import satisfies_python, is_prerelease

def parse_requirements_text(text: str) -> list:
    pkgs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = None
        version = None
        if "==" in line:
            name, version = line.split("==", 1)
        elif ">=" in line or "<=" in line or "~=" in line or "<" in line or ">" in line:
            name = line
        else:
            name = line
        pkgs.append({"spec": line, "name": name, "version": version})
    return pkgs

def scan_exact_pin(name: str, version: str, py_version: str) -> dict:
    osv = query_pypi_vulns(name, version)
    stats = summary_stats(osv)
    rp = requires_python_for_release(name, version)
    compatible = satisfies_python(rp, py_version)
    return {"name": name, "version": version, "osv": osv, "stats": stats, "requires_python": rp, "python_compatible": compatible}

def pick_highest_safe(name: str, constraint: str, py_version: str) -> dict:
    rels = releases(name)
    versions = sorted(rels.keys(), key=lambda v: v)
    best = None
    for v in versions[::-1]:
        if is_prerelease(v):
            continue
        rp = requires_python_for_release(name, v)
        if not satisfies_python(rp, py_version):
            continue
        osv = query_pypi_vulns(name, v)
        stats = summary_stats(osv)
        if stats["count"] == 0:
            best = {"name": name, "version": v, "requires_python": rp, "osv": osv, "stats": stats}
            break
    return best or {}

def run_scan(requirements_path: str, py_version: str, out_dir: str) -> dict:
    text = Path(requirements_path).read_text()
    pkgs = parse_requirements_text(text)
    results = []
    for p in pkgs:
        if p.get("version"):
            results.append(scan_exact_pin(p["name"], p["version"], py_version))
        else:
            name = p["name"].split()[0]
            res = pick_highest_safe(name, p["spec"], py_version)
            res["spec"] = p["spec"]
            results.append(res)
    aggregated = {"python_version": py_version, "count": len(results), "packages": results}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    Path(out / "scan.json").write_text(json.dumps(aggregated, ensure_ascii=False, indent=2))
    Path(out / "scan.md").write_text(render_markdown(aggregated))
    return aggregated

def render_markdown(scan: dict) -> str:
    lines = []
    lines.append(f"Python {scan['python_version']} dependency risk scan")
    lines.append("")
    for p in scan["packages"]:
        n = p.get("name")
        v = p.get("version")
        stats = p.get("stats") or {}
        lines.append(f"- {n}=={v} vulns={stats.get('count', 0)} max_cvss={stats.get('max_cvss', 0)}")
    return "\n".join(lines)

