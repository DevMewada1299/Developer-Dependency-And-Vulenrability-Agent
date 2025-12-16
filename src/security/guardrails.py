import re

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+previous\s+instructions", re.I),
    re.compile(r"(system|internal)\s+prompt", re.I),
    re.compile(r"reveal\s+(system|internal|developer).*", re.I),
    re.compile(r"repeat\s+(system|internal).*prompt", re.I),
    re.compile(r"(jailbreak|bypass|disable)\s+(guardrails|safety|filters)", re.I),
    re.compile(r"without\s+det(e|)ction", re.I),
    re.compile(r"unauthorized|illegal|off-?campus", re.I),
    re.compile(r"secret|password|api\s?key|token|credential|private\s?key", re.I),
    re.compile(r"chain[- ]of[- ]thought|\bcot\b", re.I),
    re.compile(r"do\s+not\s+obey|override\s+instructions", re.I),
]

SCOPE_PATTERNS = [
    re.compile(r"requirements?\.txt|requirements", re.I),
    re.compile(r"dependenc(y|ies)", re.I),
    re.compile(r"package(s)?", re.I),
    re.compile(r"pip(-audit)?|pip", re.I),
    re.compile(r"osv|pypi|cve", re.I),
    re.compile(r"version(s)?|pin(s)?|lock", re.I),
    re.compile(r"scan|audit", re.I),
]

def check_query(text: str) -> dict:
    t = text or ""
    inj_matches = []
    for p in INJECTION_PATTERNS:
        m = p.search(t)
        if m:
            inj_matches.append(m.group(0))
    blocked = bool(inj_matches)
    in_scope = any(p.search(t) for p in SCOPE_PATTERNS)
    return {"blocked": blocked, "matches": inj_matches, "in_scope": in_scope}
