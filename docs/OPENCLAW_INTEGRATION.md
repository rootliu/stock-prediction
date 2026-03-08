# OpenClaw Integration

## Purpose

Use `stock-prediction` in headless mode from `cron` or from an OpenClaw bot. The app writes a complete gold patrol bundle into a fixed directory, and the bot only needs to wait for `manifest.json` to appear.

## Entry Points

Direct Python launcher:

```bash
cd /Users/rootliu/code/stock-prediction
python run.py --bot-output-dir /path/to/openclaw/stock-prediction
```

OpenClaw wrapper script:

```bash
/Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /path/to/openclaw/stock-prediction
```

## Supported Conventions

The launcher accepts either:

- `--bot-output-dir /path/to/output`
- `--openclaw-output-dir /path/to/output`
- `OPENCLAW_OUTPUT_DIR=/path/to/output`

## Output Contract

The report bundle writes these files into the target directory:

- `manifest.json`
- `report.md`
- `gold_quote.json`
- `gold_prediction.json`
- `gold_history.csv`
- `gold_forecast.csv`
- `gold_compare.csv`
- `gold_session.csv`
- `gold_prediction.png`
- `gold_compare.png`
- `gold_session.png`
- `gold_summary_table.png`
- `gold_forecast_table.png`

`manifest.json` is written last and should be treated as the completion marker.

## Environment Variables For Cron

Optional environment variables used by `scripts/run_openclaw_report.sh`:

- `OPENCLAW_OUTPUT_DIR`
- `OPENCLAW_REPORT_SOURCE`
- `OPENCLAW_HORIZON`
- `OPENCLAW_LOOKBACK`
- `OPENCLAW_COMPARE_DAYS`
- `OPENCLAW_SESSION_DAYS`
- `OPENCLAW_SESSION_PERIOD`

## Cron Example

```cron
0 8,12,20 * * 1-5 OPENCLAW_OUTPUT_DIR=/path/to/openclaw/stock-prediction /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh >> /tmp/openclaw-stock-prediction.log 2>&1
```

## Current Scope

Current bot mode only generates the gold patrol bundle. MAG7 is not wired into the OpenClaw flow yet.
