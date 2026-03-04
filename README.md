# Temporal Technical-Debt Report (ChatDev GPT-5 Traces)

This README is written as a short report describing how we extract temporal, phase-level technical-debt signals from ChatDev execution traces and quantify accumulation via code-smell deltas between phases.

## Motivation

Multi-agent LLM workflows (e.g., ChatDev) are iterative: artifacts are revised across phases (Coding → Code Review → Testing). As a result, technical debt is best studied temporally (how it changes between snapshots) rather than only at the final code state.

This pipeline targets two signals:

- **Verification tunnel vision**: review/test agents prioritize correctness, sometimes introducing maintainability debt via incremental patches.
- **Debt propagation**: smells introduced in one phase constrain later phases and can compound during repeated iterations.

## What this pipeline extracts

- Token usage by phase bucket (Design/Coding/Code Review/Testing/Documentation) from `data/ChatDev_GPT-5_Trace_Analysis_Results.json`.
- Reconstructed Python snapshots:
  - `post_coding`: Python files emitted in the `Coding` phase.
  - `post_review`: Python files after applying all `CodeReviewModification` cycles.
  - `final`: final Python files present in each project trace directory.
- DPy (DesignitePython) smell counts per snapshot and deltas between snapshots.

Artifacts are written under `data/processed_data/temporal_debt/`.

## Method

For each project:

1) Parse the ChatDev `.log` to find the `Coding` phase output and extract all `*.py` code blocks.
2) Apply `CodeReviewModification` cycles to reconstruct a post-review Python snapshot.
3) Use the on-disk trace directory as the final snapshot (final Python files).
4) Run DPy on each snapshot and compute smell deltas:
   - Δreview = impl_smells(post_review) − impl_smells(post_coding)
   - Δfinal  = impl_smells(final) − impl_smells(post_review)
   - Δtotal  = impl_smells(final) − impl_smells(post_coding)

## Headline dataset stats

- Total trace projects: **30** (Python projects: **28**, non-Python: **2**).
- Implementation smells (DPy) — mean counts: post_coding=35.250, post_review=35.321, final=36.071.
- Δ implementation smells (mean / median): post_review−post_coding=0.071 / 1.000, final−post_review=0.750 / 0.000, final−post_coding=0.821 / 2.000.

Most common implementation smells in the final snapshots (top 10, aggregated):

| smell | count |
|---|---:|
| Magic number | 600 |
| Long statement | 281 |
| Complex method | 75 |
| Empty catch block | 23 |
| Long parameter list | 9 |
| Long method | 9 |
| Long identifier | 7 |
| Complex conditional | 6 |

Smell types with the largest aggregated increases (top 10):

| transition | smell | Δcount |
|---|---|---:|
| post_review−post_coding | Long statement | 21 |
| post_review−post_coding | Empty catch block | 10 |
| post_review−post_coding | Complex method | 4 |
| post_review−post_coding | Long parameter list | 1 |
| final−post_review | Magic number | 11 |
| final−post_review | Long statement | 10 |
| final−post_review | Complex method | 1 |
| final−post_review | Empty catch block | 1 |
| final−post_review | Long method | 1 |

## Top deltas (implementation smells)

### Largest Δ(post_review − post_coding)

| project | Δimpl | review_cycles | review_tokens |
|---|---:|---:|---:|
| TheCrossword | 9 | 3 | 74,258 |
| GoldMiner | 7 | 3 | 69,538 |
| DouDizhuPoker | 6 | 3 | 145,032 |
| DetectPalindromes | 5 | 3 | 62,109 |
| SnakeGame | 4 | 3 | 61,655 |

### Largest Δ(final − post_review)

| project | Δimpl | test_cycles | testing_tokens |
|---|---:|---:|---:|
| Pong | 21 | 1 | 9,369 |
| Checkers | 6 | 1 | 10,710 |
| Tiny Rouge | 5 | 0 | 0 |
| FlappyBird | 4 | 1 | 12,145 |
| StrandsNYT | 2 | 2 | 28,561 |

## Qualitative hooks

To support manual trace reading, `data/temporal_debt_results.json` includes small excerpts per project:

- `excerpts.code_review_comment`: last `CodeReviewComment` agent message (when present).
- `excerpts.last_test_reports`: last `Test Reports` block from the runtime harness.

## Reproduce

From repo root (`/home/kira`):

```bash
python3 ChatDev_GPT-5_Reasoning/scripts/temporal_debt_report.py \
  --traces ChatDev_GPT-5_Reasoning/traces \
  --token-json ChatDev_GPT-5_Reasoning/data/ChatDev_GPT-5_Trace_Analysis_Results.json \
  --out-json ChatDev_GPT-5_Reasoning/data/temporal_debt_results.json \
  --out-md ChatDev_GPT-5_Reasoning/README.md
```

Outputs:

- `data/temporal_debt_results.json`: per-project counts, deltas, and qualitative excerpts.
- `data/processed_data/temporal_debt/snapshots/`: reconstructed per-phase Python snapshots.
- `data/processed_data/temporal_debt/dpy_outputs/`: DPy JSON outputs per snapshot.

## Notes / limitations

- Two projects in this trace set are JavaScript-only (`CandyCrush`, `Tetris`) and are included in the JSON output with `python_supported=false`.
- This report focuses on DPy smell categories. If you add a second detector (e.g., PyExamine), extend the JSON schema in `data/temporal_debt_results.json` and merge deltas per stage.
- Snapshots are reconstructed from log-emitted code blocks; if a phase omits unchanged files, the pipeline uses a replace/patch heuristic controlled by `--replace-threshold`.
- `final` is the on-disk end state of each trace directory; Δfinal therefore captures all downstream edits after review (including testing and any later phases), not just `TestModification`.
