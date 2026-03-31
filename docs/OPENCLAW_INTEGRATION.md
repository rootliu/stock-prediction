# OpenClaw Integration

## Purpose

Use `stock-prediction` in headless mode from `cron` or from an OpenClaw bot. The app writes a complete gold patrol bundle into a fixed directory, and the bot only needs to wait for `manifest.json` to appear.

## Current Defaults

Current gold patrol behavior is:

- forecast granularity: `4h`
- default prediction strategy: `ensemble`
- supported rollback strategies: `boosting`, `linear`
- recommended source: `SHFE_AU_MAIN`

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

Direct scenario wrapper for timed agents:

```bash
/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /path/to/openclaw/gold-direct
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
- `external_gold_survey.csv`
- `gold_curve_comparison.csv`
- `gold_external_main_curve.csv`
- `gold_prediction.png`
- `gold_compare.png`
- `gold_session.png`
- `gold_curve_comparison.png`
- `gold_summary_table.png`
- `gold_forecast_table.png`
- `gold_external_survey_table.png`
- `gold_curve_comparison_table.png`

`manifest.json` is written last and should be treated as the completion marker.

Recommended agent read order:

1. Wait for `manifest.json`
2. Read `report.md` for the human summary
3. Read `gold_prediction.json` and `gold_forecast.csv` for structured prediction values
4. Read PNG assets only if the downstream bot needs charts or tables

## Direct Scenario Bundle

If the downstream bot wants the newer `direct + bull/base/bear` report flow instead of the older patrol bundle, use:

```bash
/Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /path/to/openclaw/gold-direct [target-end]
```

This writes a fixed bundle:

- `manifest.json`
- `report.md`
- `scenario.png`
- `scenario.csv`
- `scenario.json`

Recommended agent read order:

1. Wait for `manifest.json`
2. Read `report.md` for the ready-to-send “汇报版”
3. Read `scenario.png` if the downstream channel supports images
4. Read `scenario.csv` / `scenario.json` for structured fields

If `target-end` is omitted, the wrapper defaults to the third future trading day.

## Environment Variables For Cron

Optional environment variables used by `scripts/run_openclaw_report.sh`:

- `OPENCLAW_OUTPUT_DIR`
- `OPENCLAW_REPORT_SOURCE`
- `OPENCLAW_HORIZON`
- `OPENCLAW_LOOKBACK`
- `OPENCLAW_PREDICT_MODEL`
- `OPENCLAW_COMPARE_DAYS`
- `OPENCLAW_SESSION_DAYS`
- `OPENCLAW_SESSION_PERIOD`

Default behavior:

- `OPENCLAW_LOOKBACK=120`
- `OPENCLAW_PREDICT_MODEL=ensemble`
- `OPENCLAW_SESSION_PERIOD=4h`
- 黄金预测与主曲线对比默认按 `4h` 粒度生成

Rollback options:

- `OPENCLAW_PREDICT_MODEL=boosting`
- `OPENCLAW_PREDICT_MODEL=linear`

Force a strategy explicitly:

```bash
OPENCLAW_PREDICT_MODEL=ensemble /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/openclaw-stock-prediction
OPENCLAW_PREDICT_MODEL=boosting /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/openclaw-stock-prediction
OPENCLAW_PREDICT_MODEL=linear /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/openclaw-stock-prediction
```

## Cron Example

```cron
0 8,12,20 * * 1-5 OPENCLAW_OUTPUT_DIR=/path/to/openclaw/stock-prediction /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh >> /tmp/openclaw-stock-prediction.log 2>&1
```

## Current Scope

Current bot mode only generates the gold patrol bundle. MAG7 is not wired into the OpenClaw flow yet.
