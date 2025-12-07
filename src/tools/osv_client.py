import json
import requests

OSV_API = "https://api.osv.dev/v1/query"

def query_pypi_vulns(name: str, version: str) -> dict:
    payload = {"version": version, "package": {"name": name, "ecosystem": "PyPI"}}
    r = requests.post(OSV_API, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_ids(result: dict) -> list:
    vulns = result.get("vulns") or []
    ids = []
    for v in vulns:
        x = [v.get("id")] + [a.get("id") for a in (v.get("aliases") or []) if isinstance(a, dict) and a.get("id")]
        for i in x:
            if i and i not in ids:
                ids.append(i)
    return ids

def summary_stats(result: dict) -> dict:
    vulns = result.get("vulns") or []
    severities = []
    for v in vulns:
        for s in v.get("severity") or []:
            try:
                severities.append(float(s.get("score")))
            except Exception:
                pass
    return {"count": len(vulns), "max_cvss": max(severities) if severities else 0.0}

def first_fixed_versions(result: dict) -> list:
    vulns = result.get("vulns") or []
    fixed = []
    for v in vulns:
        ranges = []
        for a in v.get("affected") or []:
            for r in a.get("ranges") or []:
                if r.get("type") == "ECOSYSTEM":
                    ranges.append(r)
        for r in ranges:
            for e in r.get("events") or []:
                f = e.get("fixed")
                if f and f not in fixed:
                    fixed.append(f)
    return sorted(fixed)
