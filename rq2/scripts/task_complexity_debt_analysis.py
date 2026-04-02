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


def maybe_make_plots(rows: list[dict[str, Any]], plots_dir: Path) -> dict[str, str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return {}

    plots_dir.mkdir(parents=True, exist_ok=True)
    colors = {"Low": "#4C78A8", "Medium": "#F58518", "High": "#54A24B"}
    tier_order = ["Low", "Medium", "High"]
    tier_groups = {tier: [row for row in rows if row["complexity_tier"] == tier] for tier in tier_order}
    plot_paths: dict[str, str] = {}

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
