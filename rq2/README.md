# RQ2

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
- The final smell analysis covers the 28 Python projects with DPy output; `CandyCrush` and `Tetris` are excluded
