<!-- # RQ2

This folder contains the standalone analysis for:

`RQ2: How does the complexity of software tasks correlate with the technical debt accumulated in LLM-MA workflows?`

## What this version measures

- Complexity proxy: `total_reasoning_tokens`
- Complexity tiers: tertiles of `total_reasoning_tokens`
- Smell categories:
  - `Implementation` = DPy implementation smells
  - `Structural` = DPy design smells
  - `Architectural` = PyExamine architectural smells
- Supporting metric: `Diversity` = number of unique smell types at the final snapshot

## Files

- `scripts/task_complexity_debt_analysis.py`: computes the metrics, statistics, and optional plots
- `data/rq2_results.json`: machine-readable results
- `Report.md`: narrative report with tables and interpretation

## Run

```bash
python3 agent_debt/rq2/scripts/task_complexity_debt_analysis.py
```

Skip plots if `matplotlib` is unavailable:

```bash
python3 agent_debt/rq2/scripts/task_complexity_debt_analysis.py --skip-plots
```

## Inputs

- `agent_debt/data/ChatDev_GPT-5_Trace_Analysis_Results.json`
- `agent_debt/data/temporal_debt_results.json`
- `agent_debt/data/processed_data/temporal_debt/dpy_outputs`
- `agent_debt/data/processed_data/temporal_debt/snapshots`
- `python_smells_detector`

## Main takeaway

- The strongest supported RQ2 results are: higher task complexity is associated with more `Implementation` smells, more `Architectural` smells, and higher smell `Diversity`.
- `Structural` smells appear only sparsely, so their relationship with complexity is still weak in this dataset.
- Architectural smells are now computed with PyExamine, cached under `agent_debt/data/processed_data/temporal_debt/pyexamine_outputs`, and included directly in `agent_debt/rq2/data/rq2_results.json`.

See `Report.md` for the full statistical analysis and project-level appendix. -->
# RQ2: Task complexity vs architectural, structural, and implementation smells

## Research question

How does the complexity of software tasks correlate with the technical debt accumulated in LLM-MA workflows?

## Operationalization

- Dataset scope: 30 ChatDev tasks in total, with 28 Python projects analyzable by the smell pipeline. `CandyCrush` and `Tetris` are excluded because the pipeline is Python-based.
- Complexity proxy: `total_reasoning_tokens`, defined as the sum of reasoning tokens across all available phases for a project.
- Complexity tiers: tertiles on `total_reasoning_tokens`.
- Smell categories:
  - `Implementation` = DPy implementation smells
  - `Structural` = DPy design smells
  - `Architectural` = PyExamine architectural smells
- Important detector note: the analysis now uses a mixed detector setup on purpose. DPy remains the source for implementation and structural smells, while PyExamine is used to recover architectural smells.
- Additional supporting metric: `Diversity`, defined as the number of unique smell types at the final snapshot across all three smell categories.
- Inferential layer: permutation-tested Spearman correlations (`10000` permutations), Kruskal-Wallis tests across `Low / Medium / High`, and High-vs-Low effect sizes.

## Complexity tiers

The complexity proxy distribution for the 28 Python projects is:

| Metric | Value |
| :-- | --: |
| Mean total reasoning tokens | 26285.71 |
| Median total reasoning tokens | 24768.00 |
| Q1 | 22768.00 |
| Q3 | 29792.00 |
| Min | 17280.00 |
| Max | 40000.00 |

Tier thresholds:

| Tier | Rule |
| :-- | :-- |
| Low | `total_reasoning_tokens <= 23744` |
| Medium | `23744 < total_reasoning_tokens <= 27968` |
| High | `total_reasoning_tokens > 27968` |

## Main results

### 1. Complexity is associated with both implementation smells and architectural smells

| Metric | Spearman rho | Permutation p | Reading |
| :-- | --: | --: | :-- |
| Final implementation smells | 0.434 | 0.022 | positive, statistically supported |
| Final structural smells | 0.194 | 0.319 | weak, not supported |
| Final architectural smells | 0.560 | 0.002 | strong, statistically supported |
| Final diversity | 0.564 | 0.002 | strongest overall signal |
| Final total smells | 0.443 | 0.020 | positive, statistically supported |
<!-- | Delta implementation smells | 0.439 | 0.018 | positive accumulated-smell signal |
| Delta structural smells | 0.000 | 1.000 | no signal |
| Delta architectural smells | 0.404 | 0.032 | positive accumulated-smell signal |
| Delta total smells | 0.460 | 0.014 | positive accumulated-smell signal | -->

Interpretation:

- Once architectural smells are measured with PyExamine, the architecture category becomes one of the clearest RQ2 signals.
- The strongest two continuous associations are `complexity -> diversity` and `complexity -> architectural smells`.
- Implementation smells remain positively associated with complexity.
- Structural smells are still too sparse to support a reliable complexity relationship in this dataset.

### 2. Tier summaries: the clearest separation is in implementation, architecture, and diversity

| Tier | n | Impl median | Structural median | Architectural median | Total median | Diversity median |
| :-- | --: | --: | --: | --: | --: | --: |
| Low | 10 | 18.0 | 0.0 | 2.0 | 23.0 | 5.5 |
| Medium | 9 | 22.0 | 0.0 | 3.0 | 25.0 | 6.0 |
| High | 9 | 46.0 | 0.0 | 4.0 | 50.0 | 9.0 |

<!-- Accumulated smell deltas by tier:

| Tier | Delta implementation median | Delta structural median | Delta architectural median | Delta total median |
| :-- | --: | --: | --: | --: |
| Low | 0.5 | 0.0 | 0.0 | 0.5 |
| Medium | 3.0 | 0.0 | 0.0 | 3.0 |
| High | 5.0 | 0.0 | 0.0 | 5.0 | -->

Interpretation:

- Median implementation-smell count rises sharply from `18.0` in Low to `46.0` in High.
- Median architectural-smell count also increases monotonically from `2.0` to `4.0`.
- Median total smell count rises from `23.0` in Low to `50.0` in High.
- Diversity rises from `5.5` to `9.0`, meaning high-complexity tasks end with a much broader smell portfolio.
- Binary architecture presence is not informative here because PyExamine detects at least one architectural smell in every analyzed Python project; the useful signal is the **count and type** of architectural smells, not mere presence.

### 3. Inferential tests: diversity is the cleanest tier-level signal; architecture is close behind

| Metric | Kruskal-Wallis H | Epsilon squared | Tier permutation p | High-vs-Low Cliff's delta | High-vs-Low median-diff p | Reading |
| :-- | --: | --: | --: | --: | --: | :-- |
| Final implementation smells | 4.228 | 0.089 | 0.119 | 0.433 | 0.055 | positive direction, but noisy tier split |
| Final structural smells | 0.696 | 0.000 | 0.742 | 0.178 | 1.000 | no tier signal |
| Final architectural smells | 5.580 | 0.143 | 0.057 | 0.567 | 0.188 | strong direction, near-threshold tier separation |
| Final diversity | 6.582 | 0.183 | 0.032 | 0.622 | 0.050 | strongest tier-level result |
| Delta implementation smells | 2.699 | 0.028 | 0.271 | 0.300 | 0.010 | accumulated implementation growth differs most between Low and High |
| Delta architectural smells | 2.971 | 0.039 | 0.209 | 0.333 | 1.000 | positive direction, but weak tier separation |

Interpretation:

- The continuous correlation view remains more stable than the three-bin tier view.
- `Final diversity` is now the strongest tier-level result (`p = 0.032`).
- `Final architectural smells` is close to tier-level significance (`p = 0.057`) and shows a large High-vs-Low effect size.
- Implementation smells still matter, but their tier split is noisier because counts are heavy-tailed.

### 4. Smell-type profiles by tier

Implementation smell profile:

| Tier | Dominant implementation smells |
| :-- | :-- |
| Low | `Long statement` in 10/10 projects, `Complex method` in 9/10, `Magic number` in 7/10 |
| Medium | `Long statement` in 9/9, `Complex method` in 9/9, `Magic number` in 7/9 |
| High | `Long statement`, `Complex method`, and `Magic number` each in 9/9; `Long method` rises to 6/9 |

Structural smell profile:

| Tier | Structural smells observed |
| :-- | :-- |
| Low | `Multifaceted abstraction` in 2/10, `Deficient encapsulation` in 1/10 |
| Medium | `Broken modularization`, `Deficient encapsulation`, and `Feature envy` each in 1/9 |
| High | `Feature envy` in 3/9, plus `Insufficient modularization` and `Wide hierarchy` in 1/9 each |

Architectural smell profile:

| Tier | Dominant architectural smells |
| :-- | :-- |
| Low | `Potential Improper API Usage` in 10/10, `Orphan Module` in 3/10, `Unstable Dependency` in 3/10 |
| Medium | `Potential Improper API Usage` in 9/9, `Unstable Dependency` in 5/9, `Orphan Module` in 3/9 |
| High | `Potential Improper API Usage` in 9/9, `Unstable Dependency` in 8/9, `Orphan Module` in 3/9, `Scattered Functionality` in 2/9 |

Interpretation:

- The implementation profile is stable across tiers, but it intensifies in the High tier.
- The structural profile remains sparse and weak.
- The architectural profile changes more meaningfully with complexity: `Unstable Dependency` becomes much more common in the High tier (`8/9` vs `3/10` in Low), which is exactly the kind of architecture-level degradation RQ2 was meant to test.

### 5. Exceptions still matter

- `Sudoku` is in the Low tier but still ends with `139` implementation smells; it remains the major implementation outlier.
- `Chess` is in the High tier and still reduces implementation smells by `9`, but it ends with `3` architectural smells and `11` total unique smell types.
- `TheCrossword` is the most complex task by reasoning tokens (`40000`) and remains relatively clean on implementation (`24`), but it still ends with `4` architectural smells.

Interpretation:

- Complexity is a probabilistic risk signal, not a deterministic rule.
- The stronger conclusion is not “high complexity always means bad code,” but rather “high complexity shifts the distribution toward more implementation smells, more architectural smells, and higher smell diversity.”

## Answer to RQ2

Using `total_reasoning_tokens` as the task-complexity proxy, task complexity is positively associated with accumulated smells in ChatDev workflows, but the relationship is category-dependent.

- Supported conclusion: higher-complexity tasks accumulate more implementation smells.
- Newly strengthened conclusion: higher-complexity tasks also accumulate more architectural smells when architecture is measured with PyExamine.
- Strongest overall conclusion: higher-complexity tasks accumulate more diverse smell portfolios.
- Weak / unsupported conclusion: structural smells do not show a reliable statistical relationship with complexity in this sample.

The practical implication is stronger than before:

- Complexity is not only a proxy for implementation-level maintainability risk.
- It also predicts elevated architecture-level risk, especially through recurring patterns such as `Unstable Dependency` and `Potential Improper API Usage`.

For orchestration policy, this supports a broader guardrail:

- Use high reasoning-token tasks to trigger stronger implementation review.
- Also use them to trigger architecture-oriented inspection or refactoring, because complexity now shows a measurable relationship with architectural smells too.

## Limitations

- The smell analysis covers 28 Python tasks, not all 30 tasks.
- The detector setup is mixed: DPy for implementation/structural smells and PyExamine for architectural smells.
- Binary architecture presence is saturated at `100%`, so architecture conclusions depend on smell counts and smell types rather than presence/absence.
- The p-values here are exploratory and are not corrected for multiple comparisons.
- Because smell counts are heavy-tailed, medians and rank-based statistics are more reliable than means alone.

## Appendix A: Per-project table

| Project | Tier | TotalReason | FinalImpl | FinalStructural | FinalArchitecture | Diversity | DeltaImpl | DeltaStructural | DeltaArchitecture |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| TheCrossword | High | 40000 | 24 | 0 | 4 | 9 | 9 | 0 | 0 |
| Checkers | High | 37952 | 47 | 0 | 8 | 11 | 5 | 0 | 1 |
| StrandsNYT | High | 37696 | 50 | 1 | 5 | 9 | 5 | 0 | 4 |
| DouDizhuPoker | High | 32896 | 113 | 1 | 4 | 9 | 6 | 0 | 0 |
| Gomoku | High | 30656 | 46 | 0 | 4 | 5 | 1 | 0 | 1 |
| FlappyBird | High | 30336 | 29 | 0 | 5 | 8 | 5 | 0 | 0 |
| ConnectionsNYT | High | 30080 | 10 | 0 | 5 | 7 | -16 | 0 | 1 |
| MonopolyGo | High | 29696 | 27 | 1 | 2 | 7 | -1 | 0 | 0 |
| Chess | High | 29120 | 96 | 3 | 3 | 11 | -9 | 0 | -2 |
| GoldMiner | Medium | 27968 | 42 | 0 | 4 | 8 | 7 | 0 | 0 |
| SnakeGame | Medium | 27136 | 29 | 1 | 4 | 11 | 4 | 0 | 1 |
| TriviaQuiz | Medium | 27008 | 17 | 1 | 3 | 7 | 2 | 0 | 0 |
| Tiny Rouge | Medium | 26496 | 47 | 1 | 5 | 7 | 3 | 0 | 0 |
| DetectPalindromes | Medium | 25344 | 22 | 0 | 4 | 6 | 5 | 0 | 1 |
| Wordle | Medium | 24192 | 23 | 0 | 2 | 4 | 4 | 0 | 0 |
| ReversiOthello | Medium | 24064 | 16 | 0 | 2 | 4 | 0 | 0 | 0 |
| Minesweeper | Medium | 23872 | 10 | 0 | 1 | 3 | 2 | 0 | 0 |
| TextBasedSpaceInvaders | Medium | 23872 | 21 | 0 | 3 | 5 | -4 | 0 | 0 |
| StrandsGame | Low | 23744 | 46 | 1 | 3 | 9 | 0 | 0 | 0 |
| 2048 | Low | 23360 | 16 | 0 | 2 | 5 | 0 | 0 | 0 |
| BudgetTracker | Low | 22976 | 20 | 1 | 7 | 9 | 3 | 0 | 0 |
| Sudoku | Low | 22144 | 139 | 0 | 2 | 6 | 0 | 0 | 0 |
| TicTacToe | Low | 20352 | 13 | 0 | 2 | 4 | 3 | 0 | 0 |
| EpisodeChooseYourStory | Low | 20032 | 13 | 0 | 5 | 7 | 3 | 0 | 0 |
| FibonacciNumbers | Low | 19456 | 9 | 1 | 2 | 5 | 0 | 0 | 0 |
| ConnectFour | Low | 19328 | 28 | 0 | 1 | 4 | 2 | 0 | 0 |
| Mastermind | Low | 18944 | 12 | 0 | 1 | 4 | -17 | 0 | 0 |
| Pong | Low | 17280 | 45 | 0 | 3 | 7 | 1 | 0 | 0 |
