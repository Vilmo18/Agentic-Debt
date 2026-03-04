#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


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
class ProjectRatios:
    project_name: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    input_pct: float
    output_pct: float
    reasoning_pct: float

    @property
    def ratio_str(self) -> str:
        return f"{round(self.input_pct)}:{round(self.output_pct)}:{round(self.reasoning_pct)}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def compute_project_ratios(project: dict[str, Any]) -> ProjectRatios:
    name = str(project.get("project_name") or "Unknown")

    total_input = 0
    total_output = 0
    total_reasoning = 0

    for phase in project.get("phases", []) or []:
        for usage in phase.get("token_usage", []) or []:
            prompt = _safe_int(usage.get("prompt_tokens", 0))
            completion = _safe_int(usage.get("completion_tokens", 0))
            reasoning = _safe_int(usage.get("reasoning_tokens", 0))

            total_input += prompt
            total_output += completion - reasoning
            total_reasoning += reasoning

    total_tokens = total_input + total_output + total_reasoning
    if total_tokens > 0:
        input_pct = (total_input / total_tokens) * 100.0
        output_pct = (total_output / total_tokens) * 100.0
        reasoning_pct = (total_reasoning / total_tokens) * 100.0
    else:
        input_pct = output_pct = reasoning_pct = 0.0

    return ProjectRatios(
        project_name=name,
        input_tokens=total_input,
        output_tokens=total_output,
        reasoning_tokens=total_reasoning,
        total_tokens=total_tokens,
        input_pct=input_pct,
        output_pct=output_pct,
        reasoning_pct=reasoning_pct,
    )


def compute_phase_ratios(project: dict[str, Any]) -> dict[str, dict[str, float]]:
    phase_totals: dict[str, dict[str, int]] = {}

    for phase in project.get("phases", []) or []:
        phase_name = str(phase.get("phase_name") or "Unknown")
        bucket = PHASE_BUCKETS.get(phase_name, phase_name)

        totals = phase_totals.setdefault(bucket, {"input": 0, "output": 0, "reasoning": 0})
        for usage in phase.get("token_usage", []) or []:
            prompt = _safe_int(usage.get("prompt_tokens", 0))
            completion = _safe_int(usage.get("completion_tokens", 0))
            reasoning = _safe_int(usage.get("reasoning_tokens", 0))
            totals["input"] += prompt
            totals["output"] += completion - reasoning
            totals["reasoning"] += reasoning

    phase_ratios: dict[str, dict[str, float]] = {}
    for bucket, totals in phase_totals.items():
        total = totals["input"] + totals["output"] + totals["reasoning"]
        if total <= 0:
            continue
        phase_ratios[bucket] = {
            "input_pct": (totals["input"] / total) * 100.0,
            "output_pct": (totals["output"] / total) * 100.0,
            "reasoning_pct": (totals["reasoning"] / total) * 100.0,
        }

    return phase_ratios


def shapiro_pvalue(values: list[float]) -> Optional[float]:
    if len(values) < 3:
        return None
    try:
        from scipy import stats  # type: ignore
    except Exception:
        return None

    try:
        statistic, p_value = stats.shapiro(values)
    except Exception:
        return None
    try:
        return float(p_value)
    except Exception:
        return None


def format_token_ratio_table(rows: list[ProjectRatios]) -> str:
    columns: list[tuple[str, str, str]] = [
        ("Project Name", "project_name", "left"),
        ("Input Tokens", "input_tokens", "right"),
        ("Output Tokens", "output_tokens", "right"),
        ("Reasoning Tokens", "reasoning_tokens", "right"),
        ("Total Tokens", "total_tokens", "right"),
        ("Input %", "input_pct", "right_float"),
        ("Output %", "output_pct", "right_float"),
        ("Reasoning %", "reasoning_pct", "right_float"),
        ("Ratio (I:O:R)", "ratio_str", "left"),
    ]

    def cell(row: ProjectRatios, key: str, kind: str) -> str:
        v = getattr(row, key)
        if kind == "right_float":
            return f"{float(v):.6f}"
        return str(v)

    table_values: list[list[str]] = []
    widths: list[int] = [len(h) for h, _, _ in columns]
    for r in rows:
        vals: list[str] = []
        for idx, (_, key, kind) in enumerate(columns):
            s = cell(r, key, kind)
            vals.append(s)
            widths[idx] = max(widths[idx], len(s))
        table_values.append(vals)

    # Header
    out_lines: list[str] = []
    header_parts: list[str] = []
    for (h, _, kind), w in zip(columns, widths):
        header_parts.append(h.ljust(w) if kind.startswith("left") else h.rjust(w))
    out_lines.append("  ".join(header_parts))

    # Rows
    for vals in table_values:
        parts: list[str] = []
        for (h, _, kind), w, s in zip(columns, widths, vals):
            _ = h
            parts.append(s.ljust(w) if kind.startswith("left") else s.rjust(w))
        out_lines.append("  ".join(parts))

    return "\n".join(out_lines)


def _describe(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0}
    out = {
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "stdev": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
    }
    return out


def _format_sorted_percent_values(values: list[float]) -> str:
    sorted_values = sorted(values)
    values_str = ", ".join(f"{v:.0f}%" for v in sorted_values)
    wrapped = textwrap.wrap(values_str, width=80)
    return "\n".join(f"  {line}" for line in wrapped)


def write_token_ratio_outputs(rows: list[ProjectRatios], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 100

    input_pcts = [r.input_pct for r in rows]
    output_pcts = [r.output_pct for r in rows]
    reasoning_pcts = [r.reasoning_pct for r in rows]

    def write_distribution_block(
        *,
        title: str,
        values: list[float],
        include_median: bool,
    ) -> list[str]:
        stats = _describe(values)
        p = shapiro_pvalue(values)
        normality_line = (
            "Normal distribution (Shapiro-Wilk): Not enough samples (need at least 3)"
            if p is None and len(values) < 3
            else (
                "Normal distribution (Shapiro-Wilk): Skipped (scipy not installed)"
                if p is None
                else f"Normal distribution (Shapiro-Wilk): {'Yes' if p > 0.05 else 'No'} (p = {p:.4f})"
            )
        )

        lines: list[str] = []
        lines.append(f"\n{title}:")
        lines.append("-" * 50)
        lines.append(f"Mean: {stats['mean']:.2f}% (SD = {stats['stdev']:.2f}%)")
        if include_median:
            lines.append(f"Median: {stats['median']:.2f}%")
        lines.append(f"Range: {stats['min']:.0f}% - {stats['max']:.0f}%")
        lines.append(normality_line)
        lines.append("\nAll values (sorted ascending):")
        lines.append(_format_sorted_percent_values(values))
        return lines

    # token_ratios_table.txt (table + stats)
    table_path = output_dir / "token_ratios_table.txt"
    table_lines: list[str] = []
    table_lines.append("TOKEN RATIO TABLE")
    table_lines.append(sep)
    table_lines.append("")
    table_lines.append(format_token_ratio_table(rows))
    table_lines.append("")
    table_lines.append(sep)
    table_lines.append("")
    table_lines.append("SUMMARY STATISTICS:")
    table_lines.append(sep)
    table_lines.extend(write_distribution_block(title="INPUT TOKEN PERCENTAGES", values=input_pcts, include_median=False))
    table_lines.extend(write_distribution_block(title="OUTPUT TOKEN PERCENTAGES", values=output_pcts, include_median=False))
    table_lines.extend(
        write_distribution_block(title="REASONING TOKEN PERCENTAGES", values=reasoning_pcts, include_median=False)
    )
    table_lines.append("")
    table_lines.append(sep)
    table_lines.append("")
    table_lines.append(f"Total projects analyzed: {len(rows)}")
    table_path.write_text("\n".join(table_lines).rstrip() + "\n", encoding="utf-8")

    # token_ratios_summary.txt (stats only, includes median)
    summary_path = output_dir / "token_ratios_summary.txt"
    summary_lines: list[str] = []
    summary_lines.append(sep)
    summary_lines.append("TOKEN RATIO ANALYSIS SUMMARY")
    summary_lines.append(sep)
    summary_lines.append("")
    summary_lines.extend(write_distribution_block(title="INPUT TOKENS", values=input_pcts, include_median=True))
    summary_lines.extend(write_distribution_block(title="OUTPUT TOKENS", values=output_pcts, include_median=True))
    summary_lines.extend(write_distribution_block(title="REASONING TOKENS", values=reasoning_pcts, include_median=True))
    summary_lines.append("")
    summary_lines.append(sep)
    summary_lines.append("")
    summary_lines.append(f"Total projects analyzed: {len(rows)}")
    summary_path.write_text("\n".join(summary_lines).rstrip() + "\n", encoding="utf-8")


def write_phase_breakdown(projects: list[dict[str, Any]], output_dir: Path) -> None:
    fixed_phase_order = [
        "Design",
        "Coding",
        "Code Completion",
        "Code Review",
        "Testing",
        "Documentation",
    ]

    # Per-phase ratios across projects
    all_phase_ratios: dict[str, dict[str, list[float]]] = {
        phase: {"input": [], "output": [], "reasoning": []} for phase in fixed_phase_order
    }

    # Overall ratios across projects (using per-project totals)
    overall_input: list[float] = []
    overall_output: list[float] = []
    overall_reasoning: list[float] = []

    for project in projects:
        ratios = compute_project_ratios(project)
        overall_input.append(ratios.input_pct)
        overall_output.append(ratios.output_pct)
        overall_reasoning.append(ratios.reasoning_pct)

        phase_ratios = compute_phase_ratios(project)
        for phase_name, r in phase_ratios.items():
            if phase_name not in all_phase_ratios:
                continue
            all_phase_ratios[phase_name]["input"].append(r["input_pct"])
            all_phase_ratios[phase_name]["output"].append(r["output_pct"])
            all_phase_ratios[phase_name]["reasoning"].append(r["reasoning_pct"])

    def describe(values: list[float]) -> dict[str, float]:
        if not values:
            return {"n": 0.0, "mean": 0.0, "sd": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
        return {
            "n": float(len(values)),
            "mean": float(statistics.mean(values)),
            "sd": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
            "median": float(statistics.median(values)),
            "min": float(min(values)),
            "max": float(max(values)),
        }

    rows: list[dict[str, Any]] = []
    for phase in fixed_phase_order:
        vals_in = all_phase_ratios[phase]["input"]
        vals_out = all_phase_ratios[phase]["output"]
        vals_reas = all_phase_ratios[phase]["reasoning"]
        if not vals_in:
            continue
        rows.append(
            {
                "Phase": phase,
                "N": len(vals_in),
                "In": describe(vals_in),
                "Out": describe(vals_out),
                "Reas": describe(vals_reas),
            }
        )

    # OVERALL row
    rows.append(
        {
            "Phase": "OVERALL",
            "N": len(overall_input),
            "In": describe(overall_input),
            "Out": describe(overall_output),
            "Reas": describe(overall_reasoning),
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "phase_token_ratios_breakdown.txt"

    col_phase = 28
    col_n = 5
    col_stat = 10
    sep = "=" * 120

    lines: list[str] = []
    lines.append(sep)
    lines.append("PHASE-BY-PHASE TOKEN RATIO BREAKDOWN")
    lines.append(f"Based on {len(projects)} projects")
    lines.append(sep)
    lines.append("")
    lines.append("All values represent percentages (%) within each phase.")
    lines.append("N = number of projects where the phase appeared.")
    lines.append("SD = Standard Deviation (with ddof=1)")
    lines.append("")
    lines.append(sep)
    lines.append("")
    lines.append(
        f"{'Phase':<{col_phase}}{'N':>{col_n}}"
        f"{'Mean In':>{col_stat}}{'SD In':>{col_stat}}{'Med In':>{col_stat}}{'Min In':>{col_stat}}{'Max In':>{col_stat}}"
        f"{'Mean Out':>{col_stat}}{'SD Out':>{col_stat}}{'Med Out':>{col_stat}}{'Min Out':>{col_stat}}{'Max Out':>{col_stat}}"
        f"{'Mean Reas':>{col_stat}}{'SD Reas':>{col_stat}}{'Med Reas':>{col_stat}}{'Min Reas':>{col_stat}}{'Max Reas':>{col_stat}}"
    )
    lines.append("-" * 120)

    for row in rows:
        if row["Phase"] == "OVERALL":
            lines.append("-" * 120)
        in_stats = row["In"]
        out_stats = row["Out"]
        r_stats = row["Reas"]
        lines.append(
            f"{row['Phase']:<{col_phase}}{row['N']:>{col_n}}"
            f"{in_stats['mean']:>{col_stat}.1f}{in_stats['sd']:>{col_stat}.1f}{in_stats['median']:>{col_stat}.1f}{in_stats['min']:>{col_stat}.1f}{in_stats['max']:>{col_stat}.1f}"
            f"{out_stats['mean']:>{col_stat}.1f}{out_stats['sd']:>{col_stat}.1f}{out_stats['median']:>{col_stat}.1f}{out_stats['min']:>{col_stat}.1f}{out_stats['max']:>{col_stat}.1f}"
            f"{r_stats['mean']:>{col_stat}.1f}{r_stats['sd']:>{col_stat}.1f}{r_stats['median']:>{col_stat}.1f}{r_stats['min']:>{col_stat}.1f}{r_stats['max']:>{col_stat}.1f}"
        )

    lines.append("")
    lines.append(sep)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    default_input = Path("ChatDev_GPT-5_Reasoning/data/ChatDev_GPT-5_Trace_Analysis_Results.json")
    default_out_dir = Path("ChatDev_GPT-5_Reasoning/data/processed_data")
    parser = argparse.ArgumentParser(
        description="Compute input/output/reasoning token ratios from ChatDev_GPT-5_Trace_Analysis_Results.json.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_json",
        nargs="?",
        type=Path,
        default=default_input,
        help="Input JSON produced by token_usage_extractor_chatdev_gpt_5.py.",
    )
    parser.add_argument(
        "out_dir",
        nargs="?",
        type=Path,
        default=default_out_dir,
        help="Directory to write text outputs.",
    )
    parser.add_argument("--input-json", dest="input_json", type=Path, help="Same as positional input_json.")
    parser.add_argument("--out-dir", dest="out_dir", type=Path, help="Same as positional out_dir.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the formatted token ratio table to stdout.",
    )
    args = parser.parse_args()

    if not args.input_json.exists():
        raise SystemExit(f"Input JSON not found: {args.input_json}")

    data = json.loads(_read_text(args.input_json))
    projects = [p for p in data.get("projects", []) if isinstance(p, dict)]
    if not projects:
        raise SystemExit("No projects found in input JSON.")

    rows = [compute_project_ratios(p) for p in projects]
    rows.sort(key=lambda r: r.project_name.lower())

    write_token_ratio_outputs(rows, args.out_dir)
    write_phase_breakdown(projects, args.out_dir)

    if args.verbose:
        print(format_token_ratio_table(rows))

    print(f"Wrote: {args.out_dir / 'token_ratios_table.txt'}")
    print(f"Wrote: {args.out_dir / 'token_ratios_summary.txt'}")
    print(f"Wrote: {args.out_dir / 'phase_token_ratios_breakdown.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
