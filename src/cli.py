import argparse
from src.agents.dependency_agent import run_scan
from src.agents.orchestrator import advise

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    s = sub.add_parser("scan")
    s.add_argument("--requirements", required=True)
    s.add_argument("--python-version", default="3.11")
    s.add_argument("--out-dir", default="data")
    a = sub.add_parser("advise")
    a.add_argument("--query", required=True)
    a.add_argument("--provider", choices=["llama", "phi"], default="llama")
    a.add_argument("--requirements")
    a.add_argument("--python-version", default="3.11")
    a.add_argument("--out-dir", default="data")
    args = parser.parse_args()
    if args.cmd == "scan":
        run_scan(args.requirements, args.python_version, args.out_dir)
    if args.cmd == "advise":
        out = advise(args.query, args.provider, args.requirements, args.python_version, args.out_dir)
        print(out["answer_text"]) 

if __name__ == "__main__":
    main()
