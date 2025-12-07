import argparse
import json
import re
from pathlib import Path
from pdfminer.high_level import extract_text

def _clean_text(s: str) -> str:
    return re.sub(r"[\x00-\x1F\x7F]", " ", s)

def read_pdf(pdf_path: str) -> str:
    try:
        t = extract_text(pdf_path) or ""
    except Exception:
        t = ""
    t = _clean_text(t)
    if len(t.strip()) >= 200:
        return t
    ocr = read_pdf_ocr(pdf_path)
    return ocr

def read_pdf_ocr(pdf_path: str) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except Exception:
        return ""
    pages = convert_from_path(pdf_path, dpi=200)
    chunks = []
    for img in pages:
        try:
            s = pytesseract.image_to_string(img)
            chunks.append(s)
        except Exception:
            pass
    return _clean_text("\n\n".join(chunks))

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def extract_llms(text: str) -> list:
    candidates = [
        r"\bGPT[- ]?4(?:o|\.?1|\.?2)?\b",
        r"\bGPT[- ]?3(?:\.5)?\b",
        r"\bClaude(?:\s*\d+)?\b",
        r"\bLlama(?:\s*\d+)?\b",
        r"\bMistral\b",
        r"\bGemini\b",
        r"\bPaLM\b",
        r"\bPhi(?:\s*\d+)?\b",
        r"\bCohere\b",
        r"\bBedrock\b",
        r"\bOpenAI\b",
        r"\bAnthropic\b",
        r"\bMeta\b",
        r"\bQwen\b",
        r"\bDeepSeek\b",
    ]
    found = set()
    for pat in candidates:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            found.add(normalize(m.group(0)))
    return sorted(found)

def extract_vms(text: str) -> list:
    candidates = [
        r"\bAWS\s*EC2\b",
        r"\bAmazon\s*EC2\b",
        r"\bGCP\b",
        r"\bGoogle\s*Cloud\b",
        r"\bAzure\b",
        r"\bVMware\b",
        r"\bVirtualBox\b",
        r"\bKVM\b",
        r"\bProxmox\b",
        r"\bVagrant\b",
        r"\bDocker\b",
        r"\bKubernetes\b",
        r"\bVM\b",
        r"\bVirtual\s*Machine\b",
    ]
    found = set()
    for pat in candidates:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            found.add(normalize(m.group(0)))
    return sorted(found)

def extract_tools(text: str) -> list:
    candidates = [
        r"\btool\s*calling\b",
        r"\bfunction\s*calling\b",
        r"\bLangChain\b",
        r"\bLlamaIndex\b",
        r"\bHaystack\b",
        r"\bTransformers\b",
        r"\bOpenAI\s*tools\b",
        r"\bAnthropic\s*tools\b",
        r"\bMistral\s*function\s*tool\b",
        r"\bVertex\s*AI\b",
        r"\bBedrock\s*Agents\b",
    ]
    found = set()
    for pat in candidates:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            found.add(normalize(m.group(0)))
    return sorted(found)

def extract_requirements(text: str) -> list:
    lines = [normalize(x) for x in text.splitlines()]
    keys = ["guideline", "requirement", "evaluation", "testing", "deliverable", "milestone", "architecture"]
    picked = []
    for i, line in enumerate(lines):
        l = line.lower()
        if any(k in l for k in keys):
            window = lines[i:i+12]
            for w in window:
                if len(w) > 0 and not w.lower().startswith("page "):
                    picked.append(w)
    uniq = []
    seen = set()
    for p in picked:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq[:30]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = read_pdf(args.pdf_path)
    (out_dir / "proposal_text.txt").write_text(text)
    summary = {
        "llms": extract_llms(text),
        "vms": extract_vms(text),
        "tools": extract_tools(text),
        "requirements": extract_requirements(text),
    }
    (out_dir / "proposal_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
