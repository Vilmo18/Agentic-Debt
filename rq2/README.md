<!-- # RQ2

This folder contains the standalone analysis for:

`RQ2: How does the complexity of software tasks correlate with the technical debt accumulated in LLM-MA workflows?`

## Files

- `scripts/task_complexity_debt_analysis.py`: computes complexity proxies, tertile-based tiers, and correlations against final debt outcomes.
- `data/rq2_results.json`: structured output produced by the script.
- `Report.md`: narrative report with interpretation and tables.

## Run

```bash
python3 agent_debt/rq2/scripts/task_complexity_debt_analysis.py
```

## Inputs

- `agent_debt/data/ChatDev_GPT-5_Trace_Analysis_Results.json`
- `agent_debt/data/temporal_debt_results.json`

## Notes

- Primary complexity proxy: `total_reasoning_tokens`
- Complexity tiers are defined by tertiles of `total_reasoning_tokens`
- The final smell analysis covers the 28 Python projects with DPy output; `CandyCrush` and `Tetris` are excluded -->
# RQ2: Task complexity vs accumulated technical debt

## Research question

How does the complexity of software tasks correlate with the technical debt accumulated in LLM-MA workflows?

## Operationalization

- Dataset scope: 30 ChatDev tasks in total, with 28 Python projects analyzable by DPy. `CandyCrush` and `Tetris` are excluded from smell-based analysis because the RQ1 debt pipeline operates on Python artifacts.
- Primary complexity proxy: `total_reasoning_tokens`, defined as the sum of reasoning tokens across all available phases for a project.
- Debt outcomes: final smell count (`FinalTotal`), final fine-grained smell count (`FinalFine`), final coarse smell count (`FinalCoarse`), final smell diversity (`Diversity` = number of unique smell types), and accumulated smell growth (`DeltaTotal` = `FinalTotal - PostCodingTotal`).
- Tiering: tertiles on `total_reasoning_tokens`.
- Inferential layer: permutation-tested Spearman correlations (`10000` permutations), Kruskal-Wallis tests across the three tiers, and High-vs-Low effect sizes with permutation tests.

## Complexity tiers

The primary proxy distribution for the 28 Python projects is:

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

## Main findings

### 1. The clearest supported result is: higher complexity is associated with more diverse debt

| Debt metric | Spearman rho | Permutation p | Reading |
| :-- | --: | --: | :-- |
| Diversity | 0.544 | 0.004 | strongest supported signal |
| DeltaTotal | 0.439 | 0.018 | positive accumulated-debt signal |
| FinalFine | 0.434 | 0.026 | positive fine-grained debt signal |
| FinalTotal | 0.418 | 0.028 | positive overall debt signal |
| FinalCoarse | 0.194 | 0.319 | not statistically supported |

Interpretation:

- The strongest supported result is `Complexity -> Diversity`. More complex tasks do not just accumulate more smells; they accumulate a wider mix of smell types.
- `FinalFine`, `FinalTotal`, and `DeltaTotal` are also positively associated with complexity, but those effects are weaker than the diversity result.
- `FinalCoarse` is not statistically supported here. Its positive trend is descriptive only.

### 2. High-complexity tasks end with substantially more debt in median terms

| Tier | n | Median reasoning | FinalTotal mean | FinalTotal median | Diversity mean | Diversity median | DeltaTotal mean | DeltaTotal median | Coarse smell presence |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| Low | 10 | 20192 | 34.40 | 18.50 | 3.90 | 3.50 | -0.50 | 0.50 | 30.0% |
| Medium | 9 | 25344 | 25.56 | 22.00 | 4.00 | 4.00 | 2.56 | 3.00 | 33.3% |
| High | 9 | 30656 | 49.78 | 46.00 | 5.67 | 6.00 | 0.56 | 5.00 | 44.4% |

Interpretation:

- The median final debt burden rises from `18.5` in Low to `46.0` in High.
- Median diversity rises from `3.5` unique smell types in Low to `6.0` in High. This is the easiest tier pattern to understand.
- Coarse smell presence is still rare overall, but it is most common in the High tier (`44.4%` vs `30.0%` in Low).
- Mean values are less stable because the dataset is heavy-tailed. For example, `Sudoku` is a low-tier outlier with `139` final smells, which inflates the Low-tier mean. For this reason, medians and rank correlations are more trustworthy than raw means here.

Inferential checks for the tier view:

| Metric | Kruskal-Wallis H | Epsilon squared | Tier permutation p | High-vs-Low Cliff's delta | High-vs-Low median-diff p | High-vs-Low delta magnitude |
| :-- | --: | --: | --: | --: | --: | :-- |
| FinalTotal | 3.817 | 0.073 | 0.148 | 0.411 | 0.057 | medium |
| Diversity | 5.730 | 0.149 | 0.052 | 0.578 | 0.107 | large |
| DeltaTotal | 2.699 | 0.028 | 0.271 | 0.300 | 0.010 | small |

Interpretation:

- The three-bin tier test is not strong enough to claim clean separation for `FinalTotal` (`p = 0.148`). So we should not say "each tier is statistically different" for raw smell count.
- `Diversity` is the closest to a clean tier-level separation (`p = 0.052`) and also shows a large High-vs-Low effect size (`Cliff's delta = 0.578`).
- `DeltaTotal` is noisy across all three tiers, but the High-vs-Low median gap is statistically supported (`p = 0.010`).

### 3. High-complexity tasks show a broader smell profile, including more structural debt signals

| Tier | Dominant smell profile | Coarse smell profile |
| :-- | :-- | :-- |
| Low | `Long statement` appears in 10/10 projects, `Complex method` in 9/10, `Magic number` in 7/10 | `Multifaceted abstraction` in 2/10, `Deficient encapsulation` in 1/10 |
| Medium | `Long statement` in 9/9, `Complex method` in 9/9, `Magic number` in 7/9 | `Broken modularization`, `Deficient encapsulation`, and `Feature envy` each in 1/9 |
| High | `Long statement`, `Complex method`, and `Magic number` each in 9/9; `Long method` rises to 6/9 | `Feature envy` in 3/9, plus `Insufficient modularization` and `Wide hierarchy` in 1/9 each |

Interpretation:

- Fine-grained implementation debt dominates every tier. `Magic number`, `Long statement`, and `Complex method` are the recurring baseline smells across the dataset.
- What changes with complexity is the breadth of that smell profile. High-complexity tasks not only preserve the baseline smells, they add more long-method and identifier-level issues, and they show more recurring coarse design signals.
- The coarse-smell evidence is not strong enough to support a statistical conclusion. It is useful for qualitative interpretation, but not for a firm quantitative claim.

### 4. Complexity predicts accumulated debt only weakly to moderately, not deterministically

There are clear exceptions in both directions:

- High-complexity but relatively cleaner outcomes: `TheCrossword` reaches the highest reasoning-token count (`40000`) but ends with only `24` total smells.
- High-complexity with debt cleanup: `ConnectionsNYT` and `Chess` are both in the High tier, yet their `DeltaTotal` values are negative (`-16` and `-9`), meaning the final artifact contains fewer smells than the post-coding snapshot.
- Low-complexity but debt-heavy outcomes: `Sudoku` sits in the Low tier but ends with `139` final smells.

Interpretation:

- Complexity is informative, but not sufficient on its own. It works better as a risk signal than as a deterministic predictor.
- The best reading of the data is: high task complexity increases the probability of larger and more diverse debt, but project-specific implementation choices still dominate individual outcomes.

## Answer to RQ2

Task complexity, measured with `total_reasoning_tokens`, shows a positive but non-deterministic relationship with accumulated technical debt in ChatDev workflows.

- Strongest supported conclusion: more complex tasks accumulate more diverse debt.
- Supported but weaker conclusion: more complex tasks also tend to end with more fine-grained debt and larger total debt increase.
- Not supported as a firm conclusion: complexity alone predicts coarse or structural debt.

For orchestration policy, this supports a pragmatic guardrail:

- Treat high-reasoning tasks as higher-risk for broad and diverse debt.
- Use that signal to trigger stronger review or refactoring policies, but do not assume that high complexity alone guarantees severe debt in every project.
- If the goal is to predict structural debt specifically, this dataset is too weak to justify an automatic rule from complexity alone.

## Limitations

- The debt analysis covers 28 Python tasks, not all 30 tasks.
- DPy coarse smells are sparse in this dataset, so architecture/design conclusions should be treated cautiously.
- Reasoning tokens are only a proxy for complexity. They are useful operationally, but they blend intrinsic task difficulty with workflow-level effort.
- Because smell counts are heavy-tailed, mean-based comparisons alone can be misleading.
- The p-values here are exploratory and are not corrected for multiple comparisons.

## Appendix A: Per-project table

| Project | Tier | TotalReason | FinalTotal | FinalCoarse | Diversity | DeltaTotal | CodeChanges |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| TheCrossword | High | 40000 | 24 | 0 | 6 | 9 | 4 |
| Checkers | High | 37952 | 47 | 0 | 6 | 5 | 4 |
| StrandsNYT | High | 37696 | 51 | 1 | 6 | 5 | 4 |
| DouDizhuPoker | High | 32896 | 114 | 1 | 7 | 6 | 4 |
| Gomoku | High | 30656 | 46 | 0 | 3 | 1 | 4 |
| FlappyBird | High | 30336 | 29 | 0 | 4 | 5 | 4 |
| ConnectionsNYT | High | 30080 | 10 | 0 | 4 | -16 | 4 |
| MonopolyGo | High | 29696 | 28 | 1 | 6 | -1 | 4 |
| Chess | High | 29120 | 99 | 3 | 9 | -9 | 4 |
| GoldMiner | Medium | 27968 | 42 | 0 | 5 | 7 | 4 |
| SnakeGame | Medium | 27136 | 30 | 1 | 7 | 4 | 4 |
| TriviaQuiz | Medium | 27008 | 18 | 1 | 5 | 2 | 4 |
| Tiny Rouge | Medium | 26496 | 48 | 1 | 4 | 3 | 4 |
| DetectPalindromes | Medium | 25344 | 22 | 0 | 4 | 5 | 4 |
| Wordle | Medium | 24192 | 23 | 0 | 3 | 4 | 4 |
| ReversiOthello | Medium | 24064 | 16 | 0 | 3 | 0 | 4 |
| Minesweeper | Medium | 23872 | 10 | 0 | 2 | 2 | 4 |
| TextBasedSpaceInvaders | Medium | 23872 | 21 | 0 | 3 | -4 | 4 |
| StrandsGame | Low | 23744 | 47 | 1 | 6 | 0 | 4 |
| 2048 | Low | 23360 | 16 | 0 | 4 | 0 | 4 |
| BudgetTracker | Low | 22976 | 21 | 1 | 6 | 3 | 4 |
| Sudoku | Low | 22144 | 139 | 0 | 5 | 0 | 4 |
| TicTacToe | Low | 20352 | 13 | 0 | 2 | 3 | 4 |
| EpisodeChooseYourStory | Low | 20032 | 13 | 0 | 3 | 3 | 4 |
| FibonacciNumbers | Low | 19456 | 10 | 1 | 3 | 0 | 4 |
| ConnectFour | Low | 19328 | 28 | 0 | 3 | 2 | 3 |
| Mastermind | Low | 18944 | 12 | 0 | 3 | -17 | 4 |
| Pong | Low | 17280 | 45 | 0 | 4 | 1 | 4 |
