# Gold Postmortem 2026-04-07

## Scope

Review the direct-scenario forecast issued from `/Users/rootliu/code/report/gold_direct_scenario_2026-04-03.md` for the dates `2026-04-06` and `2026-04-07`.

## Forecast Snapshot

| Forecast date | Bear | Base | Bull | Base low | Base high | Confidence |
|---|---:|---:|---:|---:|---:|---:|
| 2026-04-06 | 1011.43 | 1035.73 | 1061.65 | 1015.06 | 1056.41 | 40.6% |
| 2026-04-07 | 999.13 | 1041.08 | 1085.26 | 1002.17 | 1079.99 | 56.7% |

## Actual Market Check

### 2026-04-06

- SHFE AU daily feed has no row for `2026-04-06`.
- The latest official daily rows move from `2026-04-03` directly to `2026-04-07` intraday in minute data.
- Conclusion: `2026-04-06` should not have been treated as a normal forecast target for SHFE.

### 2026-04-07

Latest observed intraday state from the fetched `60min` bars:

| Trade date | Bars | Open | High | Low | Latest observed | Latest bar time |
|---|---:|---:|---:|---:|---:|---|
| 2026-04-07 | 4 | 1034.00 | 1037.68 | 1027.84 | 1033.12 | 2026-04-07 14:45 |

## Postmortem Findings

### Finding 1: target-date alignment is the main defect

The forecast path used `pd.bdate_range`, which assumes generic weekdays. That produced a synthetic target on `2026-04-06` even though SHFE did not publish a daily trading row for that date.

Impact:

- The model labeled a non-trading day as `T+1`.
- The next real trading day, `2026-04-07`, was effectively shifted to `T+2` in the report.
- This makes the apparent forecast miss look larger than the underlying price error really was.

### Finding 2: the first real trading day was actually close to the T+1 forecast level

If we map the first forecasted real session to `2026-04-07`, the more relevant base level is the reported `2026-04-06` base forecast: `1035.73`.

Comparison against `2026-04-07` latest observed price:

- Forecast base: `1035.73`
- Latest observed: `1033.12`
- Difference: `+2.61` (`+0.25%`)

This is a small miss and sits comfortably inside the base range `[1015.06, 1056.41]`.

### Finding 3: the reported 2026-04-07 base was somewhat aggressive in level, but not directionally broken

Reported `2026-04-07` base forecast was `1041.08`.
Compared with the latest observed `2026-04-07 14:45` price `1033.12`:

- Difference: `+7.96` (`+0.77%`)
- Direction vs prior close `1033.00`: still mildly bullish, not the wrong side of the market
- The actual intraday range `1027.84 ~ 1037.68` remained inside the forecast interval `[1002.17, 1079.99]`

Interpretation:

- The model overstated intraday upside speed.
- The direction call was not obviously wrong by the latest observed bar.
- The interval remained conservative enough to contain the live move.

## Distortion Causes

1. Trading-calendar bug
   - The use of generic business days instead of SHFE trading dates created a false `2026-04-06` target.

2. Horizon shift
   - Because `T+1` landed on a non-trading day, the live `2026-04-07` session got evaluated against the `T+2` row, inflating the apparent error.

3. Event overlay narrative drift
   - The `2026-04-06` row carried a bearish explanation (`事件落地回吐`) on a day that should not have existed in the forecast table.
   - This is not just a display bug; it can mislead downstream agents.

4. Multi-day slope still slightly aggressive
   - Even after correcting the date alignment, the `2026-04-07` reported base `1041.08` was above the latest observed `1033.12`.
   - The model is still a bit too eager to extrapolate short-term upside after a strong anchor day.

## Recommended Fixes

1. Replace `pd.bdate_range` with a real SHFE trading calendar
   - Forecast targets should be generated from actual exchange sessions, not generic weekdays.

2. Add a target-date validity check before prediction output
   - If a date is not in the exchange calendar, skip it entirely instead of issuing a forecast row.

3. Separate `next trading day` from `next weekday`
   - All downstream reports and agents should speak in trading-session terms.

4. For same-day review, compare against session bars explicitly
   - Before daily close is available, compare the forecast against `open / high / low / latest observed` instead of pretending the daily result is final.

5. Slightly damp the direct model's short-horizon upside extrapolation
   - Especially when event/news factors are bullish but the actual session opens flatter than implied by the previous close.

## Bottom Line

- The biggest problem in this specific miss was calendar alignment, not price modeling.
- Once aligned to the first real trading session, the `T+1` base forecast was actually close.
- The remaining issue is smaller: the model still overestimates short-term upside speed by roughly `0.25% ~ 0.8%` on this sample.
