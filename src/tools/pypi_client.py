import requests
from packaging.requirements import Requirement

BASE = "https://pypi.org/pypi"

def project_info(name: str) -> dict:
    try:
        if any(sym in name for sym in ["<", ">", "=", "~"]):
            req = Requirement(name)
            name = req.name
    except Exception:
        pass
    r = requests.get(f"{BASE}/{name}/json", timeout=20)
    r.raise_for_status()
    return r.json()

def releases(name: str) -> dict:
    return project_info(name).get("releases") or {}

def requires_python_for_release(name: str, version: str) -> str | None:
    rels = releases(name)
    files = rels.get(version) or []
    if not files:
        return None
    rp = files[0].get("requires_python")
    return rp
