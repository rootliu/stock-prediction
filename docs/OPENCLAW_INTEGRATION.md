# OpenClaw Integration

## Purpose

Use `stock-prediction` in headless mode from `cron` or from an OpenClaw bot. Cron and timed agents should use the direct V3 scenario wrapper; the older patrol bundle remains available for legacy OpenClaw consumers.

## Current Defaults

Current cron / timed-agent behavior is:

- wrapper: `scripts/run_gold_direct_report.sh`
- analysis command: `run_gold_analysis.py --forecast-mode direct --skip-backtest`
- report type: `gold_direct_v3`
- direct guards: enabled
- recommended source: `SHFE_AU_MAIN`

## Entry Points

Direct Python launcher:

```bash
cd /Users/rootliu/code/stock-prediction
python run.py --bot-output-dir /path/to/openclaw/stock-prediction
```

Legacy OpenClaw patrol wrapper script:

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

If `target-end` is omitted, the wrapper defaults to the third future SHFE trading day.

## Environment Variables For Cron

Optional environment variables used by `scripts/run_gold_direct_report.sh`:

- `GOLD_DIRECT_OUTPUT_DIR`
- `GOLD_TARGET_END`
- `MPLCONFIGDIR`

The wrapper always calls:

```bash
run_gold_analysis.py --forecast-mode direct --skip-backtest
```

Optional environment variables used only by legacy `scripts/run_openclaw_report.sh`:

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
0 9,20 * * 1-5 /Users/rootliu/code/stock-prediction/scripts/run_gold_direct_report.sh /tmp/gold-direct-agent >> /tmp/gold-direct-agent.log 2>&1
```

## Current Scope

The direct scenario wrapper generates the gold direct V3 report bundle. MAG7 is not wired into the OpenClaw flow yet.
