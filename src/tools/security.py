import json
import subprocess
from pathlib import Path

def run_pip_audit(requirements_path: str) -> dict:
    cmd = [str(Path('.venv/bin/pip-audit')) , '-r', requirements_path, '-f', 'json']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return {"error": out.stderr.strip()}
        data = json.loads(out.stdout)
        return data
    except Exception as e:
        return {"error": str(e)}

def summarize_pip_audit(data: dict) -> dict:
    vulns = data.get('vulnerabilities') or []
    severities = {}
    for v in vulns:
        for adv in v.get('advisories') or []:
            sev = adv.get('severity') or ''
            severities[sev] = severities.get(sev, 0) + 1
    return {"count": len(vulns), "severities": severities}

