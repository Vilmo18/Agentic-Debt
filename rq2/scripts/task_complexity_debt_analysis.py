#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import statistics
import sys
import types
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any


PRIMARY_PROXY = "total_reasoning_tokens"
PYEXAMINE_PACKAGE_NAME = "_rq2_pyexamine"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return xs[int(k)]
    return xs[lower] + (xs[upper] - xs[lower]) * (k - lower)


def describe_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "n": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "stdev": 0.0,
            "min": 0.0,
            "q1": 0.0,
            "q3": 0.0,
            "max": 0.0,
        }
    xs = sorted(float(v) for v in values)
    return {
        "n": float(len(xs)),
        "mean": float(statistics.mean(xs)),
        "median": float(statistics.median(xs)),
        "stdev": float(statistics.stdev(xs)) if len(xs) > 1 else 0.0,
        "min": float(xs[0]),
        "q1": float(percentile(xs, 0.25)),
        "q3": float(percentile(xs, 0.75)),
        "max": float(xs[-1]),
    }


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else 0.0


def rank_data(values: list[float]) -> list[float]:
    indexed = sorted((float(value), idx) for idx, value in enumerate(values))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        end = start
        while end + 1 < len(indexed) and indexed[end + 1][0] == indexed[start][0]:
            end += 1
        rank = (start + end + 2) / 2.0
        for cursor in range(start, end + 1):
            ranks[indexed[cursor][1]] = rank
        start = end + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    return pearson(rank_data(xs), rank_data(ys))


def permutation_p_value_correlation(
    xs: list[float],
    ys: list[float],
    statistic,
    *,
    n_permutations: int,
    seed: int,
) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 1.0
    rng = random.Random(seed)
    observed = abs(float(statistic(xs, ys)))
    shuffled = list(float(y) for y in ys)
    extreme = 1
    for _ in range(n_permutations):
        rng.shuffle(shuffled)
        if abs(float(statistic(xs, shuffled))) >= observed - 1e-12:
            extreme += 1
    return extreme / float(n_permutations + 1)


def kruskal_wallis(groups: list[list[float]]) -> float:
    filtered = [list(map(float, group)) for group in groups if group]
    if len(filtered) < 2:
        return 0.0
    values = [value for group in filtered for value in group]
    ranks = rank_data(values)
    splits: list[list[float]] = []
    cursor = 0
    for group in filtered:
        splits.append(ranks[cursor : cursor + len(group)])
        cursor += len(group)
    n = len(values)
    h_stat = (12.0 / (n * (n + 1))) * sum((sum(rank_group) ** 2) / len(group) for rank_group, group in zip(splits, filtered))
    h_stat -= 3.0 * (n + 1)

    tie_counts = Counter(values)
    tie_sum = sum(count**3 - count for count in tie_counts.values() if count > 1)
    if tie_sum:
        correction = 1.0 - tie_sum / float(n**3 - n)
        if correction > 0:
            h_stat /= correction
    return h_stat


def permutation_p_value_groups(
    groups: list[list[float]],
    statistic,
    *,
    n_permutations: int,
    seed: int,
    absolute: bool = False,
) -> float:
    filtered = [list(map(float, group)) for group in groups if group]
    if len(filtered) < 2:
        return 1.0
    rng = random.Random(seed)
    observed = float(statistic(filtered))
    if absolute:
        observed = abs(observed)
    values = [value for group in filtered for value in group]
    sizes = [len(group) for group in filtered]
    extreme = 1
    for _ in range(n_permutations):
        rng.shuffle(values)
        cursor = 0
        permuted: list[list[float]] = []
        for size in sizes:
            permuted.append(values[cursor : cursor + size])
            cursor += size
        current = float(statistic(permuted))
        if absolute:
            current = abs(current)
        if current >= observed - 1e-12:
            extreme += 1
    return extreme / float(n_permutations + 1)


def median_difference(groups: list[list[float]]) -> float:
    if len(groups) != 2 or not groups[0] or not groups[1]:
        return 0.0
    return float(statistics.median(groups[1]) - statistics.median(groups[0]))


def mean_difference(groups: list[list[float]]) -> float:
    if len(groups) != 2 or not groups[0] or not groups[1]:
        return 0.0
    return float(statistics.mean(groups[1]) - statistics.mean(groups[0]))


def rate_difference(groups: list[list[float]]) -> float:
    if len(groups) != 2 or not groups[0] or not groups[1]:
        return 0.0
    return float((sum(groups[1]) / len(groups[1])) - (sum(groups[0]) / len(groups[0])))


def cliffs_delta(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys:
        return 0.0
    greater = 0
    lower = 0
    for x in xs:
        for y in ys:
            if x > y:
                greater += 1
            elif x < y:
                lower += 1
    return (greater - lower) / float(len(xs) * len(ys))


def cliffs_delta_magnitude(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude < 0.147:
        return "negligible"
    if magnitude < 0.33:
        return "small"
    if magnitude < 0.474:
        return "medium"
    return "large"


def sum_reasoning_tokens(phases: list[dict[str, Any]]) -> int:
    total = 0
    for phase in phases:
        for usage in phase.get("token_usage", []):
            total += int(usage.get("reasoning_tokens", 0))
    return total


def safe_top_counter(items: list[Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and isinstance(item[0], str)
            and item[0]
        ):
            counter[item[0]] += int(item[1])
    return counter


def counter_total(counter: Counter[str]) -> int:
    return int(sum(counter.values()))


def load_dpy_smell_counter(
    dpy_root: Path,
    *,
    project: str,
    snapshot: str,
    suffix: str | list[str],
) -> Counter[str]:
    counter: Counter[str] = Counter()
    output_dir = dpy_root / project / snapshot
    suffixes = [suffix] if isinstance(suffix, str) else list(suffix)
    for suffix_name in suffixes:
        for path in sorted(output_dir.glob(f"*_{suffix_name}.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                smell = item.get("Smell")
                if isinstance(smell, str) and smell:
                    counter[smell] += 1
    return counter


def load_pyexamine_architecture_classes(pyexamine_root: Path) -> tuple[type[Any], type[Any]]:
    package_dir = pyexamine_root / "src" / "code_quality_analyzer"
    if not package_dir.exists():
        raise FileNotFoundError(f"PyExamine package directory not found: {package_dir}")

    package = sys.modules.get(PYEXAMINE_PACKAGE_NAME)
    if package is None:
        package = types.ModuleType(PYEXAMINE_PACKAGE_NAME)
        package.__path__ = [str(package_dir)]
        sys.modules[PYEXAMINE_PACKAGE_NAME] = package

    for module_name in ["exceptions", "config_handler", "architectural_smell_detector"]:
        qualified_name = f"{PYEXAMINE_PACKAGE_NAME}.{module_name}"
        if qualified_name in sys.modules:
            continue
        module_path = package_dir / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(qualified_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load PyExamine module: {qualified_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)

    config_module = sys.modules[f"{PYEXAMINE_PACKAGE_NAME}.config_handler"]
    architecture_module = sys.modules[f"{PYEXAMINE_PACKAGE_NAME}.architectural_smell_detector"]
    return config_module.ConfigHandler, architecture_module.ArchitecturalSmellDetector


def run_pyexamine_architectural_smells(
    snapshot_dir: Path,
    *,
    pyexamine_root: Path,
    pyexamine_config: Path,
) -> list[dict[str, Any]]:
    if not snapshot_dir.exists():
        return []

    ConfigHandler, ArchitecturalSmellDetector = load_pyexamine_architecture_classes(pyexamine_root)
    config_handler = ConfigHandler(str(pyexamine_config))
    detector = ArchitecturalSmellDetector(config_handler.get_thresholds("architectural_smells"))
    detector.detect_smells(str(snapshot_dir))

    payload: list[dict[str, Any]] = []
    for smell in detector.architectural_smells:
        payload.append(
            {
                "Smell": str(getattr(smell, "name", "")),
                "Description": str(getattr(smell, "description", "")),
                "File": str(getattr(smell, "file_path", "")),
                "ModuleClass": str(getattr(smell, "module_class", "")),
                "Line": int(getattr(smell, "line_number", 0) or 0),
                "Severity": str(getattr(smell, "severity", "")),
            }
        )
    return payload


def load_pyexamine_architecture_counter(
    *,
    pyexamine_root: Path,
    pyexamine_config: Path,
    snapshots_root: Path,
    cache_root: Path,
    project: str,
    snapshot: str,
    force: bool,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    cache_file = cache_root / project / snapshot / f"{snapshot}_architectural_smells.json"
    payload: list[dict[str, Any]] = []

    if cache_file.exists() and not force:
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = []
        if isinstance(cached, list):
            payload = [item for item in cached if isinstance(item, dict)]
    else:
        snapshot_dir = snapshots_root / project / snapshot
        payload = run_pyexamine_architectural_smells(
            snapshot_dir,
            pyexamine_root=pyexamine_root,
            pyexamine_config=pyexamine_config,
        )
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for item in payload:
        smell = item.get("Smell")
        if isinstance(smell, str) and smell:
            counter[smell] += 1
    return counter


def assign_tier(value: float, low_high_thresholds: tuple[float, float]) -> str:
    low_upper, medium_upper = low_high_thresholds
    if value <= low_upper:
        return "Low"
    if value <= medium_upper:
        return "Medium"
    return "High"


def write_heavy_tail_rank_svg(rows: list[dict[str, Any]], output_path: Path) -> str:
    ranked_rows = sorted(rows, key=lambda row: (-float(row["final_total_smells"]), row["project"].lower()))
    values = [float(row["final_total_smells"]) for row in ranked_rows]
    if not values:
        return ""

    width = 1120
    height = 560
    left_margin = 72
    right_margin = 24
    top_margin = 84
    bottom_margin = 88
    side_panel_gap = 18
    side_panel_width = 270
    plot_right = width - right_margin - side_panel_width - side_panel_gap
    plot_width = plot_right - left_margin
    plot_height = height - top_margin - bottom_margin
    max_value = max(values)
    median_value = statistics.median(values)
    q3_value = percentile(values, 0.75)
    min_value = min(values)
    total_sum = sum(values)
    n = len(values)
    step = plot_width / max(n, 1)
    bar_width = max(3.0, step * 0.72)
    top_quartile_count = max(1, math.ceil(n * 0.25))
    top_3_share = sum(values[: min(3, n)]) / total_sum if total_sum else 0.0
    top_quartile_share = sum(values[:top_quartile_count]) / total_sum if total_sum else 0.0
    max_to_median_ratio = max_value / median_value if median_value else 0.0

    def x_pos(index: int) -> float:
        return left_margin + index * step + (step - bar_width) / 2.0

    def y_pos(value: float) -> float:
        if max_value <= 0:
            return top_margin + plot_height
        return top_margin + plot_height - (value / max_value) * plot_height

    y_ticks = sorted({0.0, median_value, q3_value, max_value})
    line_points: list[str] = []
    head_region_width = min(plot_width, top_quartile_count * step)
    summary_box_x = plot_right + side_panel_gap
    summary_box_y = 96
    summary_box_width = side_panel_width
    summary_box_height = 114
    outlier_box_x = summary_box_x
    outlier_box_y = summary_box_y + summary_box_height + 18
    outlier_box_width = summary_box_width
    outlier_box_height = 112
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        '.title { font: 700 22px sans-serif; fill: #111827; }',
        '.subtitle { font: 12px sans-serif; fill: #4b5563; }',
        '.axis { stroke: #111827; stroke-width: 1.2; }',
        '.grid { stroke: #e5e7eb; stroke-width: 1; }',
        '.bar { fill: #7ba6d8; }',
        '.bar-top { fill: #f58518; }',
        '.rank-line { fill: none; stroke: #1d4ed8; stroke-width: 2; opacity: 0.9; }',
        '.head-region { fill: #fff7ed; stroke: #fed7aa; stroke-width: 1; }',
        '.summary-box { fill: #f8fafc; stroke: #cbd5e1; stroke-width: 1; rx: 10; }',
        '.summary-title { font: 700 12px sans-serif; fill: #111827; }',
        '.summary-text { font: 12px sans-serif; fill: #334155; }',
        '.outlier-box { fill: #fff7ed; stroke: #fed7aa; stroke-width: 1; rx: 10; }',
        '.outlier-title { font: 700 12px sans-serif; fill: #9a3412; }',
        '.outlier-text { font: 12px sans-serif; fill: #7c2d12; }',
        '.marker-circle { fill: #1d4ed8; stroke: white; stroke-width: 1.5; }',
        '.marker-text { font: 10px sans-serif; font-weight: 700; fill: white; }',
        '.tick { font: 11px sans-serif; fill: #374151; }',
        '.label { font: 12px sans-serif; fill: #111827; }',
        '.note { font: 12px sans-serif; fill: #374151; }',
        '.median-line { stroke: #ef4444; stroke-width: 1.5; stroke-dasharray: 6 4; }',
        '.q3-line { stroke: #10b981; stroke-width: 1.5; stroke-dasharray: 4 4; }',
        '.quartile-label { font: 11px sans-serif; fill: #9a3412; font-weight: 700; }',
        '</style>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<rect x="{left_margin}" y="{top_margin}" width="{head_region_width:.2f}" height="{plot_height}" class="head-region"/>',
        '<text x="24" y="30" class="title">Final total smells by project (sorted descending)</text>',
        '<text x="24" y="50" class="subtitle">Projects are ranked from highest to lowest final total smells. A steep head plus a long flat tail indicates a heavy-tailed distribution.</text>',
        f'<text x="{left_margin + head_region_width / 2:.2f}" y="{top_margin - 10}" text-anchor="middle" class="quartile-label">Shaded area = top quartile of projects</text>',
    ]

    for tick in y_ticks:
        y = y_pos(tick)
        svg_parts.append(f'<line x1="{left_margin}" y1="{y:.2f}" x2="{plot_right}" y2="{y:.2f}" class="grid"/>')
        svg_parts.append(f'<text x="{left_margin - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{tick:.1f}</text>')

    svg_parts.append(f'<line x1="{left_margin}" y1="{top_margin}" x2="{left_margin}" y2="{top_margin + plot_height}" class="axis"/>')
    svg_parts.append(
        f'<line x1="{left_margin}" y1="{top_margin + plot_height}" x2="{plot_right}" y2="{top_margin + plot_height}" class="axis"/>'
    )

    median_y = y_pos(median_value)
    q3_y = y_pos(q3_value)
    svg_parts.append(
        f'<line x1="{left_margin}" y1="{median_y:.2f}" x2="{plot_right}" y2="{median_y:.2f}" class="median-line"/>'
    )
    svg_parts.append(
        f'<line x1="{left_margin}" y1="{q3_y:.2f}" x2="{plot_right}" y2="{q3_y:.2f}" class="q3-line"/>'
    )
    svg_parts.append(
        f'<text x="{plot_right - 2}" y="{median_y - 6:.2f}" text-anchor="end" class="tick">median = {median_value:.1f}</text>'
    )
    svg_parts.append(
        f'<text x="{plot_right - 2}" y="{q3_y - 6:.2f}" text-anchor="end" class="tick">Q3 = {q3_value:.1f}</text>'
    )

    for index, row in enumerate(ranked_rows):
        value = float(row["final_total_smells"])
        x = x_pos(index)
        y = y_pos(value)
        bar_height = top_margin + plot_height - y
        css_class = "bar-top" if index < 3 else "bar"
        svg_parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" class="{css_class}"/>')
        line_points.append(f"{x + bar_width / 2.0:.2f},{y:.2f}")

    svg_parts.append(f'<polyline points="{" ".join(line_points)}" class="rank-line"/>')

    for index in range(min(3, n)):
        value = values[index]
        x = x_pos(index) + bar_width / 2.0
        y = y_pos(value)
        circle_y = max(top_margin + 12, y + 14)
        svg_parts.append(f'<circle cx="{x:.2f}" cy="{circle_y:.2f}" r="10" class="marker-circle"/>')
        svg_parts.append(
            f'<text x="{x:.2f}" y="{circle_y + 3:.2f}" text-anchor="middle" class="marker-text">{index + 1}</text>'
        )

    x_tick_indices = sorted({0, max(0, n // 4), max(0, n // 2), max(0, (3 * n) // 4), n - 1})
    for idx in x_tick_indices:
        tick_x = x_pos(idx) + bar_width / 2.0
        svg_parts.append(
            f'<line x1="{tick_x:.2f}" y1="{top_margin + plot_height}" x2="{tick_x:.2f}" y2="{top_margin + plot_height + 6}" class="axis"/>'
        )
        svg_parts.append(
            f'<text x="{tick_x:.2f}" y="{top_margin + plot_height + 22}" text-anchor="middle" class="tick">{idx + 1}</text>'
        )

    svg_parts.append(
        f'<text x="{left_margin + plot_width / 2:.2f}" y="{height - 20}" text-anchor="middle" class="label">Project rank by final total smells</text>'
    )
    svg_parts.append(
        f'<text x="18" y="{top_margin + plot_height / 2:.2f}" transform="rotate(-90 18 {top_margin + plot_height / 2:.2f})" text-anchor="middle" class="label">Final total smells</text>'
    )
    svg_parts.append(
        f'<line x1="{plot_right + side_panel_gap / 2:.2f}" y1="{top_margin}" x2="{plot_right + side_panel_gap / 2:.2f}" y2="{top_margin + plot_height}" class="grid"/>'
    )
    svg_parts.append(
        f'<rect x="{summary_box_x}" y="{summary_box_y}" width="{summary_box_width}" height="{summary_box_height}" class="summary-box"/>'
    )
    svg_parts.append(f'<text x="{summary_box_x + 14}" y="{summary_box_y + 22}" class="summary-title">Heavy-tail cues</text>')
    summary_lines = [
        f'max / median = {max_to_median_ratio:.2f}x',
        f'top 3 projects = {top_3_share * 100:.1f}% of all final smells',
        f'top quartile ({top_quartile_count} projects) = {top_quartile_share * 100:.1f}%',
        f'median = {median_value:.1f}, Q3 = {q3_value:.1f}, min = {min_value:.1f}',
    ]
    for idx, line in enumerate(summary_lines):
        svg_parts.append(
            f'<text x="{summary_box_x + 14}" y="{summary_box_y + 44 + idx * 18}" class="summary-text">{escape(line)}</text>'
        )
    svg_parts.append(
        f'<rect x="{outlier_box_x}" y="{outlier_box_y}" width="{outlier_box_width}" height="{outlier_box_height}" class="outlier-box"/>'
    )
    svg_parts.append(f'<text x="{outlier_box_x + 14}" y="{outlier_box_y + 22}" class="outlier-title">Top outliers</text>')
    for idx in range(min(3, n)):
        row = ranked_rows[idx]
        value = int(values[idx])
        svg_parts.append(
            f'<text x="{outlier_box_x + 14}" y="{outlier_box_y + 44 + idx * 18}" class="outlier-text">{idx + 1}. {escape(row["project"])} = {value}</text>'
        )
    svg_parts.append(
        f'<text x="{outlier_box_x + 14}" y="{outlier_box_y + 98}" class="outlier-text">Orange bars mark the top 3 projects.</text>'
    )

    head_notes = [
        f'top outlier: {ranked_rows[0]["project"]} = {int(values[0])}',
        f'3rd highest = {ranked_rows[min(2, n - 1)]["project"]} = {int(values[min(2, n - 1)])}',
        f'min = {int(min_value)}',
    ]
    svg_parts.append(f'<text x="24" y="{height - 52}" class="note">{escape(" | ".join(head_notes))}</text>')
    svg_parts.append(
        f'<text x="24" y="{height - 32}" class="note">Interpretation: a few projects concentrate very high smell counts, while many projects remain near the low end.</text>'
    )
    svg_parts.append('</svg>')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return str(output_path)


def maybe_make_plots(rows: list[dict[str, Any]], plots_dir: Path) -> dict[str, str]:
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, str] = {}
    heavy_tail_path = plots_dir / "final_total_smells_heavy_tail.svg"
    plot_paths["final_total_smells_heavy_tail"] = write_heavy_tail_rank_svg(rows, heavy_tail_path)

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return plot_paths

    colors = {"Low": "#4C78A8", "Medium": "#F58518", "High": "#54A24B"}
    tier_order = ["Low", "Medium", "High"]
    tier_groups = {tier: [row for row in rows if row["complexity_tier"] == tier] for tier in tier_order}

    plt.figure(figsize=(8, 5))
    for tier in tier_order:
        group = tier_groups[tier]
        plt.scatter(
            [row[PRIMARY_PROXY] for row in group],
            [row["final_implementation_smells"] for row in group],
            label=tier,
            color=colors[tier],
            s=45,
            alpha=0.8,
        )
    plt.xlabel("Total reasoning tokens")
    plt.ylabel("Final implementation smells")
    plt.title("Task complexity proxy vs implementation smells")
    plt.legend()
    scatter_path = plots_dir / "complexity_vs_implementation_smells.png"
    plt.tight_layout()
    plt.savefig(scatter_path, dpi=160)
    plt.close()
    plot_paths["complexity_vs_implementation_smells"] = str(scatter_path)

    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [[row["final_implementation_smells"] for row in tier_groups[tier]] for tier in tier_order],
        tick_labels=tier_order,
    )
    plt.xlabel("Complexity tier")
    plt.ylabel("Final implementation smells")
    plt.title("Implementation smells by complexity tier")
    box_smells_path = plots_dir / "tier_boxplot_implementation_smells.png"
    plt.tight_layout()
    plt.savefig(box_smells_path, dpi=160)
    plt.close()
    plot_paths["tier_boxplot_implementation_smells"] = str(box_smells_path)

    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [[row["final_structural_smells"] for row in tier_groups[tier]] for tier in tier_order],
        tick_labels=tier_order,
    )
    plt.xlabel("Complexity tier")
    plt.ylabel("Final structural smells")
    plt.title("Structural smells by complexity tier")
    structural_boxplot_path = plots_dir / "tier_boxplot_structural_smells.png"
    plt.tight_layout()
    plt.savefig(structural_boxplot_path, dpi=160)
    plt.close()
    plot_paths["tier_boxplot_structural_smells"] = str(structural_boxplot_path)

    plt.figure(figsize=(8, 5))
    plt.boxplot(
        [[row["final_architecture_smells"] for row in tier_groups[tier]] for tier in tier_order],
        tick_labels=tier_order,
    )
    plt.xlabel("Complexity tier")
    plt.ylabel("Final architecture smells")
    plt.title("Architectural smells by complexity tier")
    architecture_boxplot_path = plots_dir / "tier_boxplot_architecture_smells.png"
    plt.tight_layout()
    plt.savefig(architecture_boxplot_path, dpi=160)
    plt.close()
    plot_paths["tier_boxplot_architecture_smells"] = str(architecture_boxplot_path)

    return plot_paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze how task complexity correlates with technical debt in ChatDev traces.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--token-json",
        type=Path,
        default=Path("agent_debt/data/ChatDev_GPT-5_Trace_Analysis_Results.json"),
    )
    parser.add_argument(
        "--debt-json",
        type=Path,
        default=Path("agent_debt/data/temporal_debt_results.json"),
    )
    parser.add_argument(
        "--dpy-root",
        type=Path,
        default=Path("agent_debt/data/processed_data/temporal_debt/dpy_outputs"),
        help="Root directory containing cached DPy outputs from the temporal debt pipeline.",
    )
    parser.add_argument(
        "--snapshots-root",
        type=Path,
        default=Path("agent_debt/data/processed_data/temporal_debt/snapshots"),
        help="Root directory containing reconstructed Python snapshots per project and phase.",
    )
    parser.add_argument(
        "--pyexamine-root",
        type=Path,
        default=Path("python_smells_detector"),
        help="Path to the local PyExamine/code_quality_analyzer checkout used for architectural smells.",
    )
    parser.add_argument(
        "--pyexamine-config",
        type=Path,
        default=Path("python_smells_detector/code_quality_config.yaml"),
        help="Configuration file for the local PyExamine/code_quality_analyzer detector.",
    )
    parser.add_argument(
        "--pyexamine-cache-dir",
        type=Path,
        default=Path("agent_debt/data/processed_data/temporal_debt/pyexamine_outputs"),
        help="Cache directory for architectural smell outputs generated via PyExamine.",
    )
    parser.add_argument(
        "--force-pyexamine",
        action="store_true",
        help="Recompute PyExamine architectural smells instead of reusing cached outputs.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("agent_debt/rq2/data/rq2_results.json"),
    )
    parser.add_argument(
        "--plots-dir",
        type=Path,
        default=Path("agent_debt/rq2/plots"),
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Do not generate PNG plots even if matplotlib is available.",
    )
    parser.add_argument(
        "--permutations",
        type=int,
        default=10000,
        help="Number of random permutations used for non-parametric p-value estimation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for permutation tests.",
    )
    args = parser.parse_args()

    token_data = read_json(args.token_json)
    debt_data = read_json(args.debt_json)
    debt_by_project = {
        row["project"]: row
        for row in debt_data.get("projects", [])
        if isinstance(row, dict) and row.get("python_supported")
    }

    rows: list[dict[str, Any]] = []
    for project in token_data.get("projects", []):
        name = project.get("project_name")
        if not isinstance(name, str) or name not in debt_by_project:
            continue

        debt_row = debt_by_project[name]
        total_reasoning_tokens = sum_reasoning_tokens(project.get("phases", []))
        coding_impl_counter = load_dpy_smell_counter(
            args.dpy_root,
            project=name,
            snapshot="post_coding",
            suffix="implementation_smells",
        )
        final_impl_counter = load_dpy_smell_counter(
            args.dpy_root,
            project=name,
            snapshot="final",
            suffix="implementation_smells",
        )
        coding_structural_counter = load_dpy_smell_counter(
            args.dpy_root,
            project=name,
            snapshot="post_coding",
            suffix="design_smells",
        )
        final_structural_counter = load_dpy_smell_counter(
            args.dpy_root,
            project=name,
            snapshot="final",
            suffix="design_smells",
        )
        coding_architecture_counter = load_pyexamine_architecture_counter(
            pyexamine_root=args.pyexamine_root,
            pyexamine_config=args.pyexamine_config,
            snapshots_root=args.snapshots_root,
            cache_root=args.pyexamine_cache_dir,
            project=name,
            snapshot="post_coding",
            force=bool(args.force_pyexamine),
        )
        final_architecture_counter = load_pyexamine_architecture_counter(
            pyexamine_root=args.pyexamine_root,
            pyexamine_config=args.pyexamine_config,
            snapshots_root=args.snapshots_root,
            cache_root=args.pyexamine_cache_dir,
            project=name,
            snapshot="final",
            force=bool(args.force_pyexamine),
        )
        final_implementation_smells = counter_total(final_impl_counter)
        final_structural_smells = counter_total(final_structural_counter)
        final_architecture_smells = counter_total(final_architecture_counter)
        final_total_smells = (
            final_implementation_smells + final_structural_smells + final_architecture_smells
        )
        final_diversity = len(
            set(final_impl_counter) | set(final_structural_counter) | set(final_architecture_counter)
        )
        delta_implementation_smells = final_implementation_smells - counter_total(coding_impl_counter)
        delta_structural_smells = final_structural_smells - counter_total(coding_structural_counter)
        delta_architecture_smells = final_architecture_smells - counter_total(coding_architecture_counter)
        delta_total_smells = (
            delta_implementation_smells + delta_structural_smells + delta_architecture_smells
        )

        rows.append(
            {
                "project": name,
                "task_prompt": project.get("task_prompt", ""),
                "software_info": project.get("software_info", {}),
                "total_reasoning_tokens": int(total_reasoning_tokens),
                "final_implementation_smells": final_implementation_smells,
                "final_structural_smells": final_structural_smells,
                "final_architecture_smells": final_architecture_smells,
                "final_total_smells": final_total_smells,
                "final_diversity": final_diversity,
                "delta_implementation_smells": delta_implementation_smells,
                "delta_structural_smells": delta_structural_smells,
                "delta_architecture_smells": delta_architecture_smells,
                "delta_total_smells": delta_total_smells,
                "structural_smell_present": 1 if final_structural_smells > 0 else 0,
                "architecture_smell_present": 1 if final_architecture_smells > 0 else 0,
                "code_change_events": int((debt_row.get("code_change") or {}).get("events", 0)),
                "impl_smell_counts": dict(final_impl_counter),
                "structural_smell_counts": dict(final_structural_counter),
                "architecture_smell_counts": dict(final_architecture_counter),
            }
        )

    if not rows:
        raise SystemExit("No overlapping Python projects were found between token and debt JSON files.")

    primary_values = [float(row[PRIMARY_PROXY]) for row in rows]
    thresholds = (
        percentile(primary_values, 1.0 / 3.0),
        percentile(primary_values, 2.0 / 3.0),
    )

    for row in rows:
        row["complexity_tier"] = assign_tier(float(row[PRIMARY_PROXY]), thresholds)

    tier_order = ["Low", "Medium", "High"]
    tier_summaries: dict[str, dict[str, Any]] = {}
    for tier in tier_order:
        group = [row for row in rows if row["complexity_tier"] == tier]
        implementation_counts: Counter[str] = Counter()
        implementation_prevalence: Counter[str] = Counter()
        structural_counts: Counter[str] = Counter()
        structural_prevalence: Counter[str] = Counter()
        architecture_counts: Counter[str] = Counter()
        architecture_prevalence: Counter[str] = Counter()

        for row in group:
            implementation_counter = Counter(row["impl_smell_counts"])
            implementation_counts.update(implementation_counter)
            for smell in implementation_counter:
                implementation_prevalence[smell] += 1

            structural_counter = Counter(row["structural_smell_counts"])
            structural_counts.update(structural_counter)
            for smell in structural_counter:
                structural_prevalence[smell] += 1

            architecture_counter = Counter(row["architecture_smell_counts"])
            architecture_counts.update(architecture_counter)
            for smell in architecture_counter:
                architecture_prevalence[smell] += 1

        tier_summaries[tier] = {
            "n_projects": len(group),
            "reasoning_tokens": describe_distribution([float(row[PRIMARY_PROXY]) for row in group]),
            "debt_metrics": {
                "final_total_smells": describe_distribution([float(row["final_total_smells"]) for row in group]),
                "final_implementation_smells": describe_distribution(
                    [float(row["final_implementation_smells"]) for row in group]
                ),
                "final_structural_smells": describe_distribution(
                    [float(row["final_structural_smells"]) for row in group]
                ),
                "final_architecture_smells": describe_distribution(
                    [float(row["final_architecture_smells"]) for row in group]
                ),
                "final_diversity": describe_distribution([float(row["final_diversity"]) for row in group]),
                "delta_implementation_smells": describe_distribution(
                    [float(row["delta_implementation_smells"]) for row in group]
                ),
                "delta_structural_smells": describe_distribution(
                    [float(row["delta_structural_smells"]) for row in group]
                ),
                "delta_architecture_smells": describe_distribution(
                    [float(row["delta_architecture_smells"]) for row in group]
                ),
                "delta_total_smells": describe_distribution([float(row["delta_total_smells"]) for row in group]),
                "code_change_events": describe_distribution([float(row["code_change_events"]) for row in group]),
            },
            "structural_smell_presence_rate": (
                float(sum(row["structural_smell_present"] for row in group) / len(group)) if group else 0.0
            ),
            "architecture_smell_presence_rate": (
                float(sum(row["architecture_smell_present"] for row in group) / len(group)) if group else 0.0
            ),
            "top_implementation_smell_counts": implementation_counts.most_common(10),
            "top_implementation_smell_project_prevalence": implementation_prevalence.most_common(10),
            "top_structural_smell_counts": structural_counts.most_common(10),
            "top_structural_smell_project_prevalence": structural_prevalence.most_common(10),
            "top_architecture_smell_counts": architecture_counts.most_common(10),
            "top_architecture_smell_project_prevalence": architecture_prevalence.most_common(10),
            "projects": sorted(row["project"] for row in group),
        }

    debt_metrics = [
        "final_total_smells",
        "final_implementation_smells",
        "final_structural_smells",
        "final_architecture_smells",
        "final_diversity",
        "delta_implementation_smells",
        "delta_structural_smells",
        "delta_architecture_smells",
        "delta_total_smells",
        "code_change_events",
    ]
    correlations: dict[str, dict[str, dict[str, float]]] = {}
    proxy_values = [float(row[PRIMARY_PROXY]) for row in rows]
    proxy_result: dict[str, dict[str, float]] = {}
    for metric in debt_metrics:
        metric_values = [float(row[metric]) for row in rows]
        proxy_result[metric] = {
            "pearson": pearson(proxy_values, metric_values),
            "spearman": spearman(proxy_values, metric_values),
            "spearman_permutation_p": permutation_p_value_correlation(
                proxy_values,
                metric_values,
                spearman,
                n_permutations=args.permutations,
                seed=args.seed,
            ),
        }
    correlations[PRIMARY_PROXY] = proxy_result

    inferential_statistics: dict[str, Any] = {
        "permutations": int(args.permutations),
        "seed": int(args.seed),
        "kruskal_wallis": {},
        "high_vs_low": {},
        "layer_presence_high_vs_low": {},
    }

    selected_tier_metrics = [
        "final_implementation_smells",
        "final_structural_smells",
        "final_architecture_smells",
        "final_diversity",
        "delta_implementation_smells",
        "delta_structural_smells",
        "delta_architecture_smells",
    ]
    for metric in selected_tier_metrics:
        metric_groups = [[float(row[metric]) for row in rows if row["complexity_tier"] == tier] for tier in tier_order]
        h_stat = kruskal_wallis(metric_groups)
        inferential_statistics["kruskal_wallis"][metric] = {
            "h_statistic": h_stat,
            "epsilon_squared": max(0.0, (h_stat - len(metric_groups) + 1.0) / (len(rows) - len(metric_groups))),
            "permutation_p": permutation_p_value_groups(
                metric_groups,
                kruskal_wallis,
                n_permutations=args.permutations,
                seed=args.seed,
            ),
        }

        low_high_groups = [
            [float(row[metric]) for row in rows if row["complexity_tier"] == "Low"],
            [float(row[metric]) for row in rows if row["complexity_tier"] == "High"],
        ]
        delta = cliffs_delta(low_high_groups[1], low_high_groups[0])
        inferential_statistics["high_vs_low"][metric] = {
            "median_low": statistics.median(low_high_groups[0]) if low_high_groups[0] else 0.0,
            "median_high": statistics.median(low_high_groups[1]) if low_high_groups[1] else 0.0,
            "median_difference": median_difference(low_high_groups),
            "median_difference_permutation_p": permutation_p_value_groups(
                low_high_groups,
                median_difference,
                n_permutations=args.permutations,
                seed=args.seed,
                absolute=True,
            ),
            "mean_difference": mean_difference(low_high_groups),
            "mean_difference_permutation_p": permutation_p_value_groups(
                low_high_groups,
                mean_difference,
                n_permutations=args.permutations,
                seed=args.seed,
                absolute=True,
            ),
            "cliffs_delta": delta,
            "cliffs_delta_magnitude": cliffs_delta_magnitude(delta),
        }

    for layer_name, presence_key in [
        ("structural", "structural_smell_present"),
        ("architecture", "architecture_smell_present"),
    ]:
        low_high_layer = [
            [float(row[presence_key]) for row in rows if row["complexity_tier"] == "Low"],
            [float(row[presence_key]) for row in rows if row["complexity_tier"] == "High"],
        ]
        inferential_statistics["layer_presence_high_vs_low"][layer_name] = {
            "rate_low": sum(low_high_layer[0]) / len(low_high_layer[0]) if low_high_layer[0] else 0.0,
            "rate_high": sum(low_high_layer[1]) / len(low_high_layer[1]) if low_high_layer[1] else 0.0,
            "rate_difference": rate_difference(low_high_layer),
            "rate_difference_permutation_p": permutation_p_value_groups(
                low_high_layer,
                rate_difference,
                n_permutations=args.permutations,
                seed=args.seed,
                absolute=True,
            ),
        }

    low_summary = tier_summaries["Low"]["debt_metrics"]
    high_summary = tier_summaries["High"]["debt_metrics"]
    comparative = {
        "high_minus_low_median_final_total_smells": (
            high_summary["final_total_smells"]["median"] - low_summary["final_total_smells"]["median"]
        ),
        "high_minus_low_median_final_implementation_smells": (
            high_summary["final_implementation_smells"]["median"]
            - low_summary["final_implementation_smells"]["median"]
        ),
        "high_minus_low_median_final_structural_smells": (
            high_summary["final_structural_smells"]["median"] - low_summary["final_structural_smells"]["median"]
        ),
        "high_minus_low_median_final_architecture_smells": (
            high_summary["final_architecture_smells"]["median"]
            - low_summary["final_architecture_smells"]["median"]
        ),
        "high_minus_low_median_final_diversity": (
            high_summary["final_diversity"]["median"] - low_summary["final_diversity"]["median"]
        ),
        "high_minus_low_structural_presence_rate": (
            tier_summaries["High"]["structural_smell_presence_rate"]
            - tier_summaries["Low"]["structural_smell_presence_rate"]
        ),
        "high_minus_low_architecture_presence_rate": (
            tier_summaries["High"]["architecture_smell_presence_rate"]
            - tier_summaries["Low"]["architecture_smell_presence_rate"]
        ),
    }

    plots: dict[str, str] = {}
    if not args.skip_plots:
        plots = maybe_make_plots(rows, args.plots_dir)

    summary = {
        "n_projects_python": len(rows),
        "primary_complexity_proxy": PRIMARY_PROXY,
        "proxy_definition": {
            PRIMARY_PROXY: "sum of reasoning_tokens across all available phases",
        },
        "smell_detector_mapping": {
            "implementation_smells": "DPy implementation_smells",
            "structural_smells": "DPy design_smells",
            "architectural_smells": "PyExamine architectural_smells",
        },
        "tiering_method": {
            "method": "tertiles on total_reasoning_tokens",
            "low_upper_threshold": thresholds[0],
            "medium_upper_threshold": thresholds[1],
        },
        "proxy_distributions": {
            PRIMARY_PROXY: describe_distribution([float(row[PRIMARY_PROXY]) for row in rows]),
        },
        "correlations": correlations,
        "inferential_statistics": inferential_statistics,
        "tiers": tier_summaries,
        "comparative": comparative,
        "plots": plots,
    }

    output_rows = []
    for row in sorted(rows, key=lambda item: (-item[PRIMARY_PROXY], item["project"].lower())):
        output_rows.append(
            {
                "project": row["project"],
                "complexity_tier": row["complexity_tier"],
                "total_reasoning_tokens": row["total_reasoning_tokens"],
                "final_total_smells": row["final_total_smells"],
                "final_implementation_smells": row["final_implementation_smells"],
                "final_structural_smells": row["final_structural_smells"],
                "final_architecture_smells": row["final_architecture_smells"],
                "final_diversity": row["final_diversity"],
                "delta_implementation_smells": row["delta_implementation_smells"],
                "delta_structural_smells": row["delta_structural_smells"],
                "delta_architecture_smells": row["delta_architecture_smells"],
                "delta_total_smells": row["delta_total_smells"],
                "structural_smell_present": row["structural_smell_present"],
                "architecture_smell_present": row["architecture_smell_present"],
                "code_change_events": row["code_change_events"],
                "top_implementation_smells": Counter(row["impl_smell_counts"]).most_common(10),
                "top_structural_smells": Counter(row["structural_smell_counts"]).most_common(10),
                "top_architecture_smells": Counter(row["architecture_smell_counts"]).most_common(10),
            }
        )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps({"summary": summary, "projects": output_rows}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote JSON: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
