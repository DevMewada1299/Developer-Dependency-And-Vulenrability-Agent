import json
from pathlib import Path
from src.tools.osv_client import query_pypi_vulns, summary_stats, first_fixed_versions
from src.tools.pypi_client import project_info, releases, requires_python_for_release
from src.util.versions import satisfies_python, is_prerelease
from packaging.version import Version
from packaging.specifiers import SpecifierSet
from packaging.requirements import Requirement

def parse_requirements_text(text: str) -> list:
    pkgs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(('-e', '--', '-c')) or line.startswith('git+'):
            continue
        try:
            req = Requirement(line)
        except Exception:
            continue
        name = req.name
        if name.lower() == 'python':
            continue
        version = None
        for s in req.specifier:
            if getattr(s, 'operator', '') == '==':
                version = s.version
                break
        pkgs.append({"spec": line, "name": name, "version": version})
    return pkgs

def scan_exact_pin(name: str, version: str, py_version: str) -> dict:
    osv = query_pypi_vulns(name, version)
    stats = summary_stats(osv)
    rp = requires_python_for_release(name, version)
    compatible = satisfies_python(rp, py_version)
    return {"name": name, "version": version, "osv": osv, "stats": stats, "requires_python": rp, "python_compatible": compatible}

def _sorted_versions(name: str) -> list:
    try:
        return sorted(releases(name).keys(), key=lambda v: Version(v))
    except Exception:
        return sorted(releases(name).keys())

def pick_highest_safe(name: str, constraint: str, py_version: str) -> dict:
    rels = releases(name)
    versions = _sorted_versions(name)
    spec = None
    try:
        spec = SpecifierSet(constraint)
    except Exception:
        spec = None
    best = None
    for v in versions[::-1]:
        if is_prerelease(v):
            continue
        if spec and Version(v) not in spec:
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

def pick_first_fixed(name: str, current_version: str, py_version: str) -> dict:
    fixes = first_fixed_versions(query_pypi_vulns(name, current_version))
    candidates = []
    for f in fixes:
        try:
            if Version(f) <= Version(current_version):
                continue
        except Exception:
            continue
        if is_prerelease(f):
            continue
        rp = requires_python_for_release(name, f)
        if not satisfies_python(rp, py_version):
            continue
        candidates.append(f)
    if not candidates:
        return {}
    target = sorted(candidates, key=lambda v: Version(v))[0]
    rp_target = requires_python_for_release(name, target)
    osv = query_pypi_vulns(name, target)
    stats = summary_stats(osv)
    return {"name": name, "version": target, "requires_python": rp_target, "osv": osv, "stats": stats}

def run_scan(requirements_path: str, py_version: str, out_dir: str) -> dict:
    text = Path(requirements_path).read_text()
    pkgs = parse_requirements_text(text)
    results = []
    for p in pkgs:
        if p.get("version"):
            results.append(scan_exact_pin(p["name"], p["version"], py_version))
        else:
            name = p["name"]
            res = pick_highest_safe(name, p["spec"], py_version)
            res["spec"] = p["spec"]
            results.append(res)
    aggregated = {"python_version": py_version, "count": len(results), "packages": results}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    Path(out / "scan.json").write_text(json.dumps(aggregated, ensure_ascii=False, indent=2))
    Path(out / "scan.md").write_text(render_markdown(aggregated))
    return aggregated

def compute_safe_pins(requirements_path: str, py_version: str, out_path: str, no_prereleases: bool = True) -> dict:
    text = Path(requirements_path).read_text()
    pkgs = parse_requirements_text(text)
    pins = []
    details = []
    for p in pkgs:
        spec = p.get("spec")
        name = p.get("name")
        current_version = p.get("version")
        if current_version:
            res = scan_exact_pin(name, current_version, py_version)
            if res.get("stats", {}).get("count", 0) > 0:
                fixed = pick_first_fixed(name, current_version, py_version)
                if fixed:
                    pins.append(f"{name}=={fixed['version']}")
                    details.append({"from": spec, "to": pins[-1], "reason": "first_fixed"})
                    continue
                # fallback to highest safe >= current
                try:
                    c = f">={current_version}"
                    pick = pick_highest_safe(name, c, py_version)
                    if pick:
                        pins.append(f"{name}=={pick['version']}")
                        details.append({"from": spec, "to": pins[-1], "reason": "highest_safe"})
                        continue
                except Exception:
                    pass
            # current is safe
            pins.append(f"{name}=={current_version}")
            details.append({"from": spec, "to": pins[-1], "reason": "unchanged"})
        else:
            # constraint or bare name
            constraint = spec
            pick = pick_highest_safe(name, constraint, py_version)
            if pick:
                pins.append(f"{pick['name']}=={pick['version']}")
                details.append({"from": spec, "to": pins[-1], "reason": "constraint_resolved"})
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(pins) + "\n")
    return {"count": len(pins), "pins_path": out_path, "pins": pins, "details": details}

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
