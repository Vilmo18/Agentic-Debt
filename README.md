# agent_debt

Temporal technical-debt (code smell) analysis over ChatDev traces.

- Analysis script: `agent_debt/scripts/temporal_debt_report.py`
- Results JSON: `agent_debt/data/temporal_debt_results.json`
- Narrative report: `agent_debt/Report.md`

## Run
```bash
python3 agent_debt/scripts/temporal_debt_report.py \
  --out-json agent_debt/data/temporal_debt_results.json
```

## Notes
- ML smells are intentionally excluded from the analysis.
- Token usage is used only as a **proxy** for verification effort (summary-level correlations; see `agent_debt/Report.md`).
- “Density” in the report refers to **smell count** (not normalized by LOC/KLOC).
- DPy outputs are cached under `agent_debt/data/processed_data/temporal_debt/`; use `--force-dpy` to recompute.
