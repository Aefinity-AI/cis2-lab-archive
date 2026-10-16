"""JSON + Markdown report generation for a conformance run."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .vectors import VectorResult


def build_json_report(
    profile: dict[str, Any],
    results: dict[str, VectorResult],
    server: str,
    gateway: str | None,
    commit: str | None,
) -> dict[str, Any]:
    return {
        "suite": "cis2-llm conformance",
        "profile": profile["name"],
        "profile_title": profile["title"],
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "server": server,
        "gateway": gateway,
        "commit": commit,
        "results": [
            {
                "vector_id": v["id"],
                "crosswalk_control": v.get("crosswalk_control"),
                "rationale": v.get("rationale"),
                **asdict(results[v["id"]]),
            }
            for v in profile["vectors"]
            if v["id"] in results
        ],
        "not_covered": profile.get("not_covered", []),
    }


def _status_emoji(status: str) -> str:
    return {"PASS": "PASS", "FAIL": "FAIL", "NOT_RUN": "NOT RUN", "BLOCKED": "BLOCKED"}.get(status, status)


def build_markdown_report(json_report: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# cis2-llm conformance report — profile `{json_report['profile']}`")
    lines.append("")
    lines.append(json_report["profile_title"])
    lines.append("")
    lines.append(f"- Generated: {json_report['generated']}")
    lines.append(f"- Server: {json_report['server']}")
    lines.append(f"- Gateway: {json_report['gateway'] or '(not provided)'}")
    lines.append(f"- Commit: {json_report['commit'] or 'unknown'}")
    lines.append("")

    counts: dict[str, int] = {}
    for r in json_report["results"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    lines.append(f"**Summary:** {summary}")
    lines.append("")
    lines.append(
        "PASS = ran and demonstrated the property. FAIL = ran and did NOT demonstrate the "
        "property (a real gap). NOT_RUN = the vector was never exercised (missing "
        "infrastructure, e.g. no --gateway URL given). BLOCKED = it WAS exercised but the "
        "current cis2-llm build has a known, honestly-documented gap that makes the check "
        "meaningless or the property genuinely absent — see detail. BLOCKED is not a pass."
    )
    lines.append("")
    lines.append("| Vector | Crosswalk control | Status | Receipt id(s) | Detail |")
    lines.append("|---|---|---|---|---|")
    for r in json_report["results"]:
        rids = ", ".join(r.get("receipt_ids") or []) or "-"
        detail = (r.get("detail") or "").replace("|", "/").replace("\n", " ")
        if len(detail) > 220:
            detail = detail[:217] + "..."
        lines.append(
            f"| `{r['vector_id']}` | {r.get('crosswalk_control') or '-'} | "
            f"{_status_emoji(r['status'])} | {rids} | {detail} |"
        )
    lines.append("")

    lines.append("## What this profile does NOT prove")
    lines.append("")
    for item in json_report["not_covered"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Per-vector detail")
    lines.append("")
    for r in json_report["results"]:
        lines.append(f"### `{r['vector_id']}` — {_status_emoji(r['status'])}")
        lines.append("")
        lines.append(f"- Crosswalk control: {r.get('crosswalk_control') or '-'}")
        lines.append(f"- Rationale: {r.get('rationale') or '-'}")
        lines.append(f"- Receipt id(s): {', '.join(r.get('receipt_ids') or []) or '(none)'}")
        lines.append(f"- Detail: {r.get('detail')}")
        lines.append("")

    return "\n".join(lines)


def write_reports(json_report: dict[str, Any], out_dir: Path, stem: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(json_report, indent=2, default=str) + "\n")
    md_path.write_text(build_markdown_report(json_report))
    return json_path, md_path
