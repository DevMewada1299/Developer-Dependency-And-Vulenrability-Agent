import argparse
from src.agents.dependency_agent import run_scan, compute_safe_pins
from src.agents.orchestrator import advise

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    s = sub.add_parser("scan")
    s.add_argument("--requirements", required=True)
    s.add_argument("--python-version", default="3.11")
    s.add_argument("--out-dir", default="data")
    p = sub.add_parser("pin")
    p.add_argument("--requirements", required=True)
    p.add_argument("--python-version", default="3.11")
    p.add_argument("--out-path", default="data/safe_requirements.txt")
    a = sub.add_parser("advise")
    a.add_argument("--query", required=True)
    a.add_argument("--provider", choices=["llama", "phi"], default="llama")
    a.add_argument("--requirements")
    a.add_argument("--python-version", default="3.11")
    a.add_argument("--out-dir", default="data")
    a.add_argument("--prompt-style", choices=["compact_json", "react_json", "deliberate_json", "strict_schema"], default="compact_json")
    a.add_argument("--planning-mode", choices=["single", "consensus-3", "consensus-5"], default="single")
    a.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.cmd == "scan":
        run_scan(args.requirements, args.python_version, args.out_dir)
    if args.cmd == "pin":
        out = compute_safe_pins(args.requirements, args.python_version, args.out_path)
        print(out["pins_path"])
    if args.cmd == "advise":
        out = advise(args.query, args.provider, args.requirements, args.python_version, args.out_dir, prompt_style=args.prompt_style, planning_mode=args.planning_mode, verify=args.verify)
        print(out["answer_text"]) 

if __name__ == "__main__":
    main()
