#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


PHASE_BUCKETS: dict[str, str] = {
    "DemandAnalysis": "Design",
    "LanguageChoose": "Design",
    "Coding": "Coding",
    "CodeComplete": "Code Completion",
    "CodeReviewComment": "Code Review",
    "CodeReviewModification": "Code Review",
    "TestErrorSummary": "Testing",
    "TestModification": "Testing",
    "EnvironmentDoc": "Documentation",
    "Reflection": "Documentation",
    "Manual": "Documentation",
}


@dataclass(frozen=True)
class LogMessage:
    role: str
    header: str
    start_line: int  # 0-based line index in the original log
    body_lines: list[str]


MESSAGE_HEADER_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} .*? INFO\] (.*?): \*\*(.*?)\*\*$")
TIMESTAMP_LINE_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} .*? INFO\] ")

PY_CODEBLOCK_RE = re.compile(
    r"(?ms)^\s*([A-Za-z0-9_./-]+\.py)\s*$\n+```python\s*\n(.*?)\n```\s*$"
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_log_messages(lines: list[str]) -> list[LogMessage]:
    messages: list[LogMessage] = []
    current_role: Optional[str] = None
    current_header: Optional[str] = None
    current_start: Optional[int] = None
    current_body: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_header, current_start, current_body
        if current_role is None or current_header is None or current_start is None:
            return
        messages.append(
            LogMessage(
                role=current_role,
                header=current_header,
                start_line=current_start,
                body_lines=current_body,
            )
        )
        current_role = None
        current_header = None
        current_start = None
        current_body = []

    for i, line in enumerate(lines):
        m = MESSAGE_HEADER_RE.match(line)
        if m:
            flush()
            current_role = m.group(1)
            current_header = m.group(2)
            current_start = i
            current_body = []
            continue

        if TIMESTAMP_LINE_RE.match(line):
            flush()
            continue

        if current_role is not None:
            current_body.append(line)

    flush()
    return messages


def extract_python_files_from_message(message: LogMessage) -> dict[str, str]:
    body = "\n".join(message.body_lines)
    files = {}
    for fname, code in PY_CODEBLOCK_RE.findall(body):
        files[fname] = code
    return files


def load_final_python_snapshot(project_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(project_dir.rglob("*.py")):
        rel = path.relative_to(project_dir).as_posix()
        files[rel] = _read_text(path)
    return files


def apply_updates(
    base_state: dict[str, str],
    updates: Iterable[dict[str, str]],
    *,
    replace_threshold: float,
) -> dict[str, str]:
    state = dict(base_state)
    for files in updates:
        if not files:
            continue
        ratio = len(files) / max(1, len(state))
        if ratio >= replace_threshold:
            state = dict(files)
        else:
            state.update(files)
    return state


def find_dpy_binary(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser()

    cwd_candidate = Path.cwd() / "DPy"
    if cwd_candidate.exists():
        return cwd_candidate

    # script is ChatDev_GPT-5_Reasoning/scripts/*.py; DPy is at repo root (/home/kira/DPy)
    script_candidate = Path(__file__).resolve().parents[2] / "DPy"
    return script_candidate


def run_dpy(dpy_path: Path, input_dir: Path, output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(dpy_path), "analyze", "-i", str(input_dir), "-o", str(output_dir), "-f", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            "DPy failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{res.stdout}\n"
            f"stderr:\n{res.stderr}\n"
        )

    def read_smells(suffix: str) -> list[dict[str, Any]]:
        matches = list(output_dir.glob(f"*_{suffix}.json"))
        if not matches:
            return []
        # DPy writes exactly one file per category; if multiple exist, merge.
        out: list[dict[str, Any]] = []
        for p in matches:
            try:
                data = json.loads(_read_text(p))
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                out.extend([d for d in data if isinstance(d, dict)])
        return out

    return {
        "architecture_smells": read_smells("architecture_smells"),
        "design_smells": read_smells("design_smells"),
        "implementation_smells": read_smells("implementation_smells"),
        "ml_smells": read_smells("ml_smells"),
    }


def bucket_token_totals(project_token_data: dict[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = Counter()
    for phase in project_token_data.get("phases", []):
        phase_name = phase.get("phase_name")
        bucket = PHASE_BUCKETS.get(phase_name, phase_name or "Unknown")
        for usage in phase.get("token_usage", []):
            totals[bucket] += int(usage.get("total_tokens", 0))
    return dict(totals)


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = sum((x - mx) ** 2 for x in xs)
    deny = sum((y - my) ** 2 for y in ys)
    den = math.sqrt(denx * deny)
    return num / den if den else 0.0


def extract_last_phase_message_excerpt(
    messages: list[LogMessage],
    *,
    phase_substring: str,
    max_lines: int,
) -> str:
    phase_msgs = [m for m in messages if phase_substring in m.header]
    if not phase_msgs:
        return ""
    body = phase_msgs[-1].body_lines
    excerpt = "\n".join(body[:max_lines]).strip()
    return excerpt


def extract_last_test_reports_excerpt(lines: list[str], *, max_lines: int = 60) -> str:
    # Find last "[Test Reports]" header and capture subsequent non-timestamp lines.
    last_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "Test Reports" in lines[i] and ("**[Test Reports]**" in lines[i] or "[Test Reports]" in lines[i]):
            last_idx = i
            break
    if last_idx is None:
        return ""

    captured: list[str] = [lines[last_idx].strip()]
    for j in range(last_idx + 1, min(last_idx + 1 + max_lines, len(lines))):
        if TIMESTAMP_LINE_RE.match(lines[j]):
            break
        captured.append(lines[j].rstrip())
    return "\n".join(captured).strip()


def write_snapshot(snapshot_dir: Path, files: dict[str, str]) -> None:
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for rel, code in files.items():
        p = snapshot_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract temporal technical debt signals from ChatDev traces and generate a report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--traces", type=Path, default=Path("ChatDev_GPT-5_Reasoning/traces"))
    parser.add_argument(
        "--token-json",
        type=Path,
        default=Path("ChatDev_GPT-5_Reasoning/data/ChatDev_GPT-5_Trace_Analysis_Results.json"),
        help="Token usage summary JSON (produced by token_usage_extractor_chatdev_gpt_5.py).",
    )
    parser.add_argument("--dpy", type=str, default=None, help="Path to the DPy binary.")
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("ChatDev_GPT-5_Reasoning/data/temporal_debt_results.json"),
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=Path("ChatDev_GPT-5_Reasoning/README.md"),
        help="Markdown report output path (overwritten).",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("ChatDev_GPT-5_Reasoning/data/processed_data/temporal_debt"),
        help="Where to store reconstructed snapshots and DPy outputs.",
    )
    parser.add_argument(
        "--replace-threshold",
        type=float,
        default=0.6,
        help="If an update outputs >= this fraction of current files, treat it as a full replacement snapshot.",
    )
    parser.add_argument(
        "--max-excerpt-lines",
        type=int,
        default=40,
        help="Max lines to keep for qualitative excerpts in the JSON output.",
    )
    args = parser.parse_args()

    dpy_path = find_dpy_binary(args.dpy)
    if not dpy_path.exists():
        raise SystemExit(f"DPy not found at: {dpy_path}")

    token_data = json.loads(_read_text(args.token_json)) if args.token_json.exists() else {}
    token_projects = {p.get("project_name"): p for p in token_data.get("projects", []) if isinstance(p, dict)}

    traces_dir: Path = args.traces
    if not traces_dir.exists():
        raise SystemExit(f"Traces dir not found: {traces_dir}")

    artifacts_dir: Path = args.artifacts_dir
    snapshots_dir = artifacts_dir / "snapshots"
    dpy_dir = artifacts_dir / "dpy_outputs"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    dpy_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    agg_impl_smells: dict[str, Counter[str]] = {
        "post_coding": Counter(),
        "post_review": Counter(),
        "final": Counter(),
    }

    log_files = sorted(traces_dir.rglob("*.log"))
    for log_path in log_files:
        project_dir = log_path.parent
        project_name = project_dir.name.split("_DefaultOrganization_")[0]

        log_lines = _read_text(log_path).splitlines()
        messages = parse_log_messages(log_lines)

        # Token + meta are always collected when available, even for non-Python projects.
        token_project = token_projects.get(project_name, {})
        bucketed_tokens = bucket_token_totals(token_project) if token_project else {}
        review_tokens = int(bucketed_tokens.get("Code Review", 0))
        test_tokens = int(bucketed_tokens.get("Testing", 0))

        review_cycles = sum(1 for m in messages if "on : CodeReviewModification" in m.header)
        test_cycles = sum(1 for m in messages if "on : TestModification" in m.header)

        review_excerpt = extract_last_phase_message_excerpt(
            messages,
            phase_substring="on : CodeReviewComment",
            max_lines=args.max_excerpt_lines,
        )
        test_excerpt = extract_last_test_reports_excerpt(log_lines, max_lines=args.max_excerpt_lines)

        coding_msgs = [m for m in messages if "on : Coding" in m.header]
        coding_files = extract_python_files_from_message(coding_msgs[0]) if coding_msgs else {}

        final_files = load_final_python_snapshot(project_dir)
        python_supported = bool(coding_files or final_files)

        counts: dict[str, Any]
        deltas: dict[str, Any]

        if not python_supported:
            counts = {"post_coding": None, "post_review": None, "final": None}
            deltas = {
                "impl_post_review_minus_post_coding": None,
                "impl_final_minus_post_review": None,
                "impl_final_minus_post_coding": None,
            }
            results.append(
                {
                    "project": project_name,
                    "log_path": str(log_path),
                    "dir_path": str(project_dir),
                    "python_supported": False,
                    "review_cycles": review_cycles,
                    "test_cycles": test_cycles,
                    "tokens": {
                        "by_bucket": bucketed_tokens,
                        "code_review_total_tokens": review_tokens,
                        "testing_total_tokens": test_tokens,
                    },
                    "counts": counts,
                    "deltas": deltas,
                    "excerpts": {
                        "code_review_comment": review_excerpt,
                        "last_test_reports": test_excerpt,
                    },
                    "software_info": token_project.get("software_info", {}),
                }
            )
            continue

        # If we cannot reconstruct post_coding from the log (rare), fall back to final snapshot.
        post_coding_files = coding_files if coding_files else final_files

        review_mod_msgs = [m for m in messages if "on : CodeReviewModification" in m.header]
        review_updates = [extract_python_files_from_message(m) for m in review_mod_msgs]
        post_review_files = apply_updates(
            post_coding_files,
            review_updates,
            replace_threshold=args.replace_threshold,
        )

        # Final snapshot comes from the on-disk trace directory by default.
        final_snapshot_files = final_files if final_files else post_review_files

        # Persist snapshots to disk (reproducibility).
        project_snap_root = snapshots_dir / project_name
        post_coding_dir = project_snap_root / "post_coding"
        post_review_dir = project_snap_root / "post_review"
        final_dir = project_snap_root / "final"
        write_snapshot(post_coding_dir, post_coding_files)
        write_snapshot(post_review_dir, post_review_files)
        write_snapshot(final_dir, final_snapshot_files)

        # Run DPy.
        smells_coding = run_dpy(dpy_path, post_coding_dir, dpy_dir / project_name / "post_coding")
        smells_review = run_dpy(dpy_path, post_review_dir, dpy_dir / project_name / "post_review")
        smells_final = run_dpy(dpy_path, final_dir, dpy_dir / project_name / "final")

        def impl_smell_counts(smells: dict[str, list[dict[str, Any]]]) -> Counter[str]:
            c: Counter[str] = Counter()
            for d in smells.get("implementation_smells", []):
                smell = d.get("Smell")
                if isinstance(smell, str) and smell:
                    c[smell] += 1
            return c

        counts = {
            "post_coding": {
                "arch": len(smells_coding["architecture_smells"]),
                "design": len(smells_coding["design_smells"]),
                "impl": len(smells_coding["implementation_smells"]),
                "ml": len(smells_coding["ml_smells"]),
                "impl_top": impl_smell_counts(smells_coding).most_common(10),
                "n_files": len(post_coding_files),
            },
            "post_review": {
                "arch": len(smells_review["architecture_smells"]),
                "design": len(smells_review["design_smells"]),
                "impl": len(smells_review["implementation_smells"]),
                "ml": len(smells_review["ml_smells"]),
                "impl_top": impl_smell_counts(smells_review).most_common(10),
                "n_files": len(post_review_files),
            },
            "final": {
                "arch": len(smells_final["architecture_smells"]),
                "design": len(smells_final["design_smells"]),
                "impl": len(smells_final["implementation_smells"]),
                "ml": len(smells_final["ml_smells"]),
                "impl_top": impl_smell_counts(smells_final).most_common(10),
                "n_files": len(final_snapshot_files),
            },
        }

        agg_impl_smells["post_coding"].update(impl_smell_counts(smells_coding))
        agg_impl_smells["post_review"].update(impl_smell_counts(smells_review))
        agg_impl_smells["final"].update(impl_smell_counts(smells_final))

        delta_review = counts["post_review"]["impl"] - counts["post_coding"]["impl"]
        delta_final = counts["final"]["impl"] - counts["post_review"]["impl"]
        delta_total = counts["final"]["impl"] - counts["post_coding"]["impl"]

        results.append(
            {
                "project": project_name,
                "log_path": str(log_path),
                "dir_path": str(project_dir),
                "python_supported": True,
                "review_cycles": review_cycles,
                "test_cycles": test_cycles,
                "tokens": {
                    "by_bucket": bucketed_tokens,
                    "code_review_total_tokens": review_tokens,
                    "testing_total_tokens": test_tokens,
                },
                "counts": counts,
                "deltas": {
                    "impl_post_review_minus_post_coding": delta_review,
                    "impl_final_minus_post_review": delta_final,
                    "impl_final_minus_post_coding": delta_total,
                },
                "excerpts": {
                    "code_review_comment": review_excerpt,
                    "last_test_reports": test_excerpt,
                },
                "software_info": token_project.get("software_info", {}),
            }
        )

    # Aggregate summary statistics (Python subset).
    python_rows = [r for r in results if r.get("python_supported")]
    impl_coding = [r["counts"]["post_coding"]["impl"] for r in python_rows]
    impl_review = [r["counts"]["post_review"]["impl"] for r in python_rows]
    impl_final = [r["counts"]["final"]["impl"] for r in python_rows]
    deltas_review = [r["deltas"]["impl_post_review_minus_post_coding"] for r in python_rows]
    deltas_final = [r["deltas"]["impl_final_minus_post_review"] for r in python_rows]
    deltas_total = [r["deltas"]["impl_final_minus_post_coding"] for r in python_rows]

    delta_review_pos_frac = (
        sum(1 for d in deltas_review if d > 0) / len(deltas_review) if deltas_review else 0
    )
    delta_final_pos_frac = (
        sum(1 for d in deltas_final if d > 0) / len(deltas_final) if deltas_final else 0
    )
    delta_total_pos_frac = (
        sum(1 for d in deltas_total if d > 0) / len(deltas_total) if deltas_total else 0
    )

    # Token correlations (only where token data exists).
    rows_with_tokens = [r for r in python_rows if r["tokens"]["code_review_total_tokens"] > 0]
    review_token_corr = pearson(
        [float(r["tokens"]["code_review_total_tokens"]) for r in rows_with_tokens],
        [float(r["deltas"]["impl_post_review_minus_post_coding"]) for r in rows_with_tokens],
    )
    rows_with_test_tokens = [r for r in python_rows if r["tokens"]["testing_total_tokens"] > 0]
    test_token_corr = pearson(
        [float(r["tokens"]["testing_total_tokens"]) for r in rows_with_test_tokens],
        [float(r["deltas"]["impl_final_minus_post_review"]) for r in rows_with_test_tokens],
    )

    delta_smells_review = agg_impl_smells["post_review"] - agg_impl_smells["post_coding"]
    delta_smells_final = agg_impl_smells["final"] - agg_impl_smells["post_review"]

    summary = {
        "n_projects_total": len(results),
        "n_projects_python": len(python_rows),
        "implementation_smells": {
            "post_coding_mean": statistics.mean(impl_coding) if impl_coding else 0,
            "post_review_mean": statistics.mean(impl_review) if impl_review else 0,
            "final_mean": statistics.mean(impl_final) if impl_final else 0,
            "delta_review_mean": statistics.mean(deltas_review) if deltas_review else 0,
            "delta_review_median": statistics.median(deltas_review) if deltas_review else 0,
            "delta_final_mean": statistics.mean(deltas_final) if deltas_final else 0,
            "delta_final_median": statistics.median(deltas_final) if deltas_final else 0,
            "delta_total_mean": statistics.mean(deltas_total) if deltas_total else 0,
            "delta_total_median": statistics.median(deltas_total) if deltas_total else 0,
            "delta_review_positive_fraction": delta_review_pos_frac,
            "delta_final_positive_fraction": delta_final_pos_frac,
            "delta_total_positive_fraction": delta_total_pos_frac,
            "top_impl_smells_final": agg_impl_smells["final"].most_common(10),
            "top_impl_smell_increases_review": delta_smells_review.most_common(10),
            "top_impl_smell_increases_final": delta_smells_final.most_common(10),
        },
        "correlations": {
            "pearson(code_review_tokens, delta_review_impl_smells)": review_token_corr,
            "pearson(testing_tokens, delta_final_impl_smells)": test_token_corr,
        },
    }

    out_payload = {"summary": summary, "projects": results}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")

    # Markdown report
    def fmt_float(x: float) -> str:
        return f"{x:.3f}"

    def fmt_int(x: float | int) -> str:
        return f"{int(x):,}"

    out_md_dir = args.out_md.parent.resolve()

    def md_rel(path: Path) -> str:
        try:
            return path.resolve().relative_to(out_md_dir).as_posix()
        except Exception:
            return path.as_posix()

    top_review = sorted(
        python_rows,
        key=lambda r: r["deltas"]["impl_post_review_minus_post_coding"],
        reverse=True,
    )[:5]
    top_final = sorted(
        python_rows,
        key=lambda r: r["deltas"]["impl_final_minus_post_review"],
        reverse=True,
    )[:5]

    md_lines: list[str] = []
    md_lines.append("# Temporal Technical-Debt Report (ChatDev GPT-5 Traces)")
    md_lines.append("")
    md_lines.append(
        "This README is written as a short report describing how we extract temporal, phase-level technical-debt signals from ChatDev execution traces "
        "and quantify accumulation via code-smell deltas between phases."
    )
    md_lines.append("")
    md_lines.append("## Motivation")
    md_lines.append("")
    md_lines.append(
        "Multi-agent LLM workflows (e.g., ChatDev) are iterative: artifacts are revised across phases (Coding → Code Review → Testing). "
        "As a result, technical debt is best studied temporally (how it changes between snapshots) rather than only at the final code state."
    )
    md_lines.append("")
    md_lines.append("This pipeline targets two signals:")
    md_lines.append("")
    md_lines.append("- **Verification tunnel vision**: review/test agents prioritize correctness, sometimes introducing maintainability debt via incremental patches.")
    md_lines.append("- **Debt propagation**: smells introduced in one phase constrain later phases and can compound during repeated iterations.")
    md_lines.append("")
    md_lines.append("## What this pipeline extracts")
    md_lines.append("")
    md_lines.append("- Token usage by phase bucket (Design/Coding/Code Review/Testing/Documentation) from `data/ChatDev_GPT-5_Trace_Analysis_Results.json`.")
    md_lines.append("- Reconstructed Python snapshots:")
    md_lines.append("  - `post_coding`: Python files emitted in the `Coding` phase.")
    md_lines.append("  - `post_review`: Python files after applying all `CodeReviewModification` cycles.")
    md_lines.append("  - `final`: final Python files present in each project trace directory.")
    md_lines.append("- DPy (DesignitePython) smell counts per snapshot and deltas between snapshots.")
    md_lines.append("")
    md_lines.append("Artifacts are written under `data/processed_data/temporal_debt/`.")
    md_lines.append("")
    md_lines.append("## Method")
    md_lines.append("")
    md_lines.append("For each project:")
    md_lines.append("")
    md_lines.append("1) Parse the ChatDev `.log` to find the `Coding` phase output and extract all `*.py` code blocks.")
    md_lines.append("2) Apply `CodeReviewModification` cycles to reconstruct a post-review Python snapshot.")
    md_lines.append("3) Use the on-disk trace directory as the final snapshot (final Python files).")
    md_lines.append("4) Run DPy on each snapshot and compute smell deltas:")
    md_lines.append("   - Δreview = impl_smells(post_review) − impl_smells(post_coding)")
    md_lines.append("   - Δfinal  = impl_smells(final) − impl_smells(post_review)")
    md_lines.append("   - Δtotal  = impl_smells(final) − impl_smells(post_coding)")
    md_lines.append("")
    md_lines.append("## Headline dataset stats")
    md_lines.append("")
    md_lines.append(f"- Total trace projects: **{summary['n_projects_total']}** (Python projects: **{summary['n_projects_python']}**, non-Python: **{summary['n_projects_total']-summary['n_projects_python']}**).")
    md_lines.append(
        "- Implementation smells (DPy) — mean counts: "
        f"post_coding={fmt_float(summary['implementation_smells']['post_coding_mean'])}, "
        f"post_review={fmt_float(summary['implementation_smells']['post_review_mean'])}, "
        f"final={fmt_float(summary['implementation_smells']['final_mean'])}."
    )
    md_lines.append(
        "- Δ implementation smells (mean / median): "
        f"post_review−post_coding={fmt_float(summary['implementation_smells']['delta_review_mean'])} / "
        f"{fmt_float(summary['implementation_smells']['delta_review_median'])}, "
        f"final−post_review={fmt_float(summary['implementation_smells']['delta_final_mean'])} / "
        f"{fmt_float(summary['implementation_smells']['delta_final_median'])}, "
        f"final−post_coding={fmt_float(summary['implementation_smells']['delta_total_mean'])} / "
        f"{fmt_float(summary['implementation_smells']['delta_total_median'])}."
    )
    md_lines.append("")
    md_lines.append("Most common implementation smells in the final snapshots (top 10, aggregated):")
    md_lines.append("")
    md_lines.append("| smell | count |")
    md_lines.append("|---|---:|")
    for smell, count in summary["implementation_smells"]["top_impl_smells_final"]:
        md_lines.append(f"| {smell} | {count} |")
    md_lines.append("")
    md_lines.append("Smell types with the largest aggregated increases (top 10):")
    md_lines.append("")
    md_lines.append("| transition | smell | Δcount |")
    md_lines.append("|---|---|---:|")
    for smell, count in summary["implementation_smells"]["top_impl_smell_increases_review"]:
        md_lines.append(f"| post_review−post_coding | {smell} | {count} |")
    for smell, count in summary["implementation_smells"]["top_impl_smell_increases_final"]:
        md_lines.append(f"| final−post_review | {smell} | {count} |")
    md_lines.append("")
    md_lines.append("## Top deltas (implementation smells)")
    md_lines.append("")
    md_lines.append("### Largest Δ(post_review − post_coding)")
    md_lines.append("")
    md_lines.append("| project | Δimpl | review_cycles | review_tokens |")
    md_lines.append("|---|---:|---:|---:|")
    for r in top_review:
        md_lines.append(
            f"| {r['project']} | {r['deltas']['impl_post_review_minus_post_coding']} | "
            f"{r['review_cycles']} | {fmt_int(r['tokens']['code_review_total_tokens'])} |"
        )
    md_lines.append("")
    md_lines.append("### Largest Δ(final − post_review)")
    md_lines.append("")
    md_lines.append("| project | Δimpl | test_cycles | testing_tokens |")
    md_lines.append("|---|---:|---:|---:|")
    for r in top_final:
        md_lines.append(
            f"| {r['project']} | {r['deltas']['impl_final_minus_post_review']} | "
            f"{r['test_cycles']} | {fmt_int(r['tokens']['testing_total_tokens'])} |"
        )
    md_lines.append("")
    md_lines.append("## Qualitative hooks")
    md_lines.append("")
    md_lines.append("To support manual trace reading, `data/temporal_debt_results.json` includes small excerpts per project:")
    md_lines.append("")
    md_lines.append("- `excerpts.code_review_comment`: last `CodeReviewComment` agent message (when present).")
    md_lines.append("- `excerpts.last_test_reports`: last `Test Reports` block from the runtime harness.")
    md_lines.append("")
    md_lines.append("## Reproduce")
    md_lines.append("")
    md_lines.append("From repo root (`/home/kira`):")
    md_lines.append("")
    md_lines.append("```bash")
    md_lines.append("python3 ChatDev_GPT-5_Reasoning/scripts/temporal_debt_report.py \\")
    md_lines.append("  --traces ChatDev_GPT-5_Reasoning/traces \\")
    md_lines.append("  --token-json ChatDev_GPT-5_Reasoning/data/ChatDev_GPT-5_Trace_Analysis_Results.json \\")
    md_lines.append("  --out-json ChatDev_GPT-5_Reasoning/data/temporal_debt_results.json \\")
    md_lines.append("  --out-md ChatDev_GPT-5_Reasoning/README.md")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("Outputs:")
    md_lines.append("")
    md_lines.append("- `data/temporal_debt_results.json`: per-project counts, deltas, and qualitative excerpts.")
    md_lines.append("- `data/processed_data/temporal_debt/snapshots/`: reconstructed per-phase Python snapshots.")
    md_lines.append("- `data/processed_data/temporal_debt/dpy_outputs/`: DPy JSON outputs per snapshot.")
    md_lines.append("")
    md_lines.append("## Notes / limitations")
    md_lines.append("")
    md_lines.append(
        "- Two projects in this trace set are JavaScript-only (`CandyCrush`, `Tetris`) and are included in the JSON output with `python_supported=false`."
    )
    md_lines.append(
        "- This report focuses on DPy smell categories. If you add a second detector (e.g., PyExamine), "
        "extend the JSON schema in `data/temporal_debt_results.json` and merge deltas per stage."
    )
    md_lines.append(
        "- Snapshots are reconstructed from log-emitted code blocks; if a phase omits unchanged files, "
        "the pipeline uses a replace/patch heuristic controlled by `--replace-threshold`."
    )
    md_lines.append(
        "- `final` is the on-disk end state of each trace directory; Δfinal therefore captures all downstream edits after review (including testing and any later phases), not just `TestModification`."
    )

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
