from packaging.version import Version
from packaging.specifiers import SpecifierSet

def satisfies_python(requires_python: str | None, py_version: str) -> bool:
    if not requires_python:
        return True
    try:
        s = SpecifierSet(requires_python)
        return Version(py_version) in s
    except Exception:
        return True

def is_prerelease(version: str) -> bool:
    try:
        return Version(version).is_prerelease
    except Exception:
        return False

