"""python -m conformance run --profile <name> --server <url> [--gateway <url>]

Runs a named compliance profile's vectors against a live cis2-llm server
(and optionally gateway), emits a JSON + Markdown report. See
conformance/CONFORMANCE.md.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import report as report_mod
from .vectors import VECTORS, Context

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


def _list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def _load_profile(name: str) -> dict:
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"unknown profile {name!r}; available: {_list_profiles()}")
    return json.loads(path.read_text())


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def cmd_run(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    is_local = args.server.startswith("http://127.0.0.1") or args.server.startswith("http://localhost")
    ctx = Context(server=args.server.rstrip("/"), gateway=(args.gateway.rstrip("/") if args.gateway else None), local_repo=is_local)

    results = {}
    for v in profile["vectors"]:
        vid = v["id"]
        fn = VECTORS.get(vid)
        if fn is None:
            print(f"WARNING: profile references unknown vector {vid!r}, skipping", file=sys.stderr)
            continue
        print(f"-- running vector: {vid} --", file=sys.stderr)
        try:
            result = fn(ctx)
        except Exception as e:  # never let a vector crash the whole run into a fake result
            from .vectors import VectorResult

            result = VectorResult(vid, "FAIL", f"vector implementation raised: {e!r}")
        print(f"   {result.status}: {result.detail}", file=sys.stderr)
        results[vid] = result

    json_report = report_mod.build_json_report(profile, results, args.server, args.gateway, _git_commit())
    out_dir = Path(args.out_dir)
    stem = f"conformance-{args.profile}"
    json_path, md_path = report_mod.write_reports(json_report, out_dir, stem)
    print(f"wrote {json_path}", file=sys.stderr)
    print(f"wrote {md_path}", file=sys.stderr)

    any_fail = any(r.status == "FAIL" for r in results.values())
    return 1 if any_fail else 0


def cmd_list_profiles(_args: argparse.Namespace) -> int:
    for name in _list_profiles():
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m conformance")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run a profile's vectors against a live server")
    run.add_argument("--profile", required=True, help=f"one of: {', '.join(_list_profiles())}")
    run.add_argument("--server", required=True, help="base URL of a running cis2-llm server, e.g. http://127.0.0.1:8799")
    run.add_argument("--gateway", default=None, help="base URL of a running cis2-llm gateway (optional; enables replay_tamper/tool_gate_deny)")
    run.add_argument("--out-dir", default=str(REPO_ROOT / "conformance" / "reports"), help="where to write JSON/MD reports")
    run.set_defaults(func=cmd_run)

    lp = sub.add_parser("list-profiles", help="list available profile names")
    lp.set_defaults(func=cmd_list_profiles)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
