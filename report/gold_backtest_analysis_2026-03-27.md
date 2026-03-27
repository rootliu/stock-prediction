# Gold Forecast Backtest Analysis — 2026-03-27

## 1. Prediction vs Reality (T+1 Check)

### Yesterday's Prediction (03-27)

| Metric | Value |
|--------|-------|
| 03-26 Close | 995.98 |
| Model Prediction (03-27) | 1010.31 (+14.33, bullish) |
| Confidence | 50.3% |

### Actual Market Data (03-27)

| Session | Open | High | Low | Close |
|---------|------|------|-----|-------|
| Night (03-26 22:00 ~ 03-27 02:00) | 990.90 | 1001.34 | 978.10 | 981.76 |
| Day (03-27 09:30 ~ 13:45 current) | 981.78 | 994.22 | 978.80 | 991.88 |

### Error Analysis

| Metric | Value |
|--------|-------|
| Prediction | 1010.31 (bullish +14.33) |
| Actual (13:45) | 991.88 (bearish -4.10) |
| Absolute Error | +18.43 CNY/g (overestimate) |
| Percentage Error | 1.86% |
| Direction | WRONG (predicted UP, actual DOWN) |

---

## 2. Full Backtest Results (stride=5, lookback=240, horizon=5)

Sample size: 838 origins, 12570 records total.

### Model Comparison

| Model | Horizon | MAE | RMSE | MAPE% | Direction% |
|-------|---------|-----|------|-------|------------|
| **linear** | T+1 | 5.81 | 8.83 | 1.59 | 50.0 |
| **linear** | T+2 | 8.34 | 16.12 | 2.20 | 52.1 |
| **linear** | T+3 | 12.27 | 19.97 | 3.27 | 50.1 |
| **linear** | T+4 | 14.51 | 23.84 | 3.83 | 51.8 |
| **linear** | T+5 | 18.30 | 29.53 | 4.82 | 53.3 |
| **boosting** | T+1 | 3.53 | 6.36 | 0.92 | 47.6 |
| **boosting** | T+2 | 5.45 | 12.82 | 1.36 | 48.6 |
| **boosting** | T+3 | 7.15 | 13.88 | 1.83 | 48.8 |
| **boosting** | T+4 | 8.91 | 17.27 | 2.23 | 49.6 |
| **boosting** | T+5 | 10.69 | 21.46 | 2.67 | 49.5 |
| **ensemble** | T+1 | 3.72 | 6.68 | 0.99 | 49.8 |
| **ensemble** | T+2 | 5.67 | 13.24 | 1.47 | 51.8 |
| **ensemble** | T+3 | 7.54 | 14.17 | 1.98 | 49.9 |
| **ensemble** | T+4 | 8.93 | 16.42 | 2.31 | 50.2 |
| **ensemble** | T+5 | 10.91 | 20.28 | 2.81 | 51.4 |

### Key Findings

1. **Direction accuracy ~50% across ALL models** — essentially coin-flip level, no predictive edge on direction.
2. **Boosting has lowest MAE/MAPE** but worst direction accuracy (47.6% at T+1).
3. **Linear has highest MAE** but marginally better direction accuracy.
4. **Ensemble is a compromise** — MAPE between linear and boosting, direction ~50%.
5. **Error grows rapidly**: T+1 MAE ~3.5-5.8 -> T+5 MAE ~10.7-18.3 (3x growth).

---

## 3. Diagnosis: Why the Model Failed

### Problem 1: Bullish Bias in Trending Markets

The model predicted +14.33 on a day that actually went -4.10. The recent price history shows:
- 03-20: 1042.02
- 03-23: 942.80 (-9.5%)
- 03-24: 979.80 (+3.9%)
- 03-25: 1013.96 (+3.5%)
- 03-26: 995.98 (-1.8%)

The model saw two consecutive up days (03-24, 03-25) and extrapolated momentum, but missed:
- The V-shape recovery was losing steam (03-26 already reversed)
- Night session COMEX sold off hard, dragging SHFE down

### Problem 2: No Night Session / Overnight Gap Information

The model trains on **daily 16:00 close** only. It has zero visibility into:
- Night session (21:00-02:30) price action
- COMEX overnight moves
- Overnight gap risk

Today's prediction was made based on 03-26 16:00 close (995.98), but by 03-27 02:00 the night session had already dropped to 981.76 (-1.43%). The model was +14.33 bullish while the market was already -14.22 by the time the day session opened.

### Problem 3: Extreme Volatility Regime

- 5-day daily volatility: **5.42%** (annualized ~86%)
- Normal gold volatility: ~15-20% annualized
- Current vol is **4-5x normal** — the model's extreme filter (2x sigma compression by 40%) is inadequate

### Problem 4: Cross-Market Adjustment Too Weak

The cross-market adjustment averaged only **+0.02 CNY/g** over the last 20 days, with a cap of +/-0.3% (~3 CNY/g). When COMEX drops 1-2% overnight, a 3 CNY/g cap is meaningless.

### Problem 5: Direction Accuracy = Random

The backtest confirms **~50% direction accuracy** — the model has no edge in predicting direction. The "confidence" metric (50.3%) was honest, but the system still output a strong bullish signal (+14.33).

---

## 4. Improvement Plan

### Priority 1: Night Session Gap Integration (High Impact, Medium Effort)

**Problem**: Model ignores 21:00-02:30 night session data.

**Solution**: Before making the T+1 prediction, fetch the latest available night session close and use it as the "effective current price" instead of the previous day's 16:00 close.

```
Implementation:
1. In sequential_forecast(), check if current time > 09:00
2. If yes, fetch SHFE AU 60min K-line for last night
3. Use night_close as the base for T+1 prediction instead of prev_day_close
4. Adjust features (lag_1 etc.) to reflect overnight move
```

**Expected Impact**: Eliminate 60-80% of overnight gap errors.

### Priority 2: Volatility-Adaptive Prediction Dampening (High Impact, Low Effort)

**Problem**: In high-vol regimes (current ~86% annualized vs normal ~15%), model still makes large directional bets.

**Solution**: Scale prediction magnitude inversely with realized volatility regime.

```
Implementation in _weighted_combine():
1. Compute 10-day realized vol (annualized)
2. Define vol regimes:
   - Normal: < 25%  -> dampening = 1.0 (no change)
   - High:   25-50% -> dampening = 0.6
   - Extreme: > 50% -> dampening = 0.3
3. Apply: predicted_change = raw_change * dampening
```

**Expected Impact**: Reduce MAE by 30-50% in high-vol periods.

### Priority 3: Direction Head Overhaul (High Impact, High Effort)

**Problem**: 50% direction accuracy = no signal.

**Solution A — Conservative**: Remove direction prediction entirely. Output a confidence interval instead.

**Solution B — Upgrade**: Add these direction-specific features:
- Night session direction (up/down from 16:00 close to night close)
- COMEX overnight return (as a leading indicator)
- Intraday momentum (slope of last 3 hours)
- Order flow imbalance (volume at bid vs ask, if available)
- RSI divergence (price vs RSI direction mismatch)

```
Implementation:
1. Create new feature builder: overnight_features()
   - night_return = night_close / prev_close - 1
   - comex_overnight_return
   - overnight_range = (night_high - night_low) / prev_close
2. Train a separate GBM direction classifier with these features
3. Only trust direction when classifier confidence > 65%
4. Below 65%, output "neutral" instead of forced up/down
```

**Expected Impact**: Direction accuracy from 50% -> 58-65%.

### Priority 4: Cross-Market Signal Amplification (Medium Impact, Low Effort)

**Problem**: Cross-market cap of +/-0.3% is too tight.

**Solution**:
- Increase cap to +/-1.0% in high-vol regimes
- Add COMEX overnight return as a direct feature (not just premium z-score)
- Weight DXY signal higher (gold-dollar correlation strengthens during crises)

```
Implementation in compute_cross_market_adjustment():
1. Dynamic cap: cap = 0.003 * close * vol_multiplier
   where vol_multiplier = max(1.0, realized_vol / normal_vol)
2. Add COMEX overnight return signal:
   comex_overnight = comex_close_today / comex_close_yesterday - 1
   adj += comex_overnight * 0.3 * close  (30% pass-through)
```

**Expected Impact**: Reduce overnight gap error by 20-30%.

### Priority 5: Confidence Calibration (Medium Impact, Low Effort)

**Problem**: Confidence of 50.3% still triggers a strong +14.33 bullish prediction.

**Solution**: When confidence < 55%, force prediction toward zero change.

```
Implementation in _weighted_combine():
1. If confidence < 55%:
   combined = prev_close + (combined - prev_close) * (confidence / 55) * 0.5
2. Output risk warning when confidence < 55%
```

**Expected Impact**: Reduce false-signal rate.

### Priority 6: Ensemble Weight Decay (Low Impact, Low Effort)

**Problem**: Equal-ish weighting of models that are all ~50% directional.

**Solution**: Implement recency-weighted model scoring — weight backtest performance from last 30 days 3x more than older periods.

### Priority 7: Intraday Prediction Support (Future)

**Problem**: Daily predictions are too coarse for active traders.

**Solution**: Add 4H prediction mode using SHFE AU 60min K-line data, with session-aware features.

---

## 5. Implementation Roadmap

| Phase | Items | Effort | Impact |
|-------|-------|--------|--------|
| **Week 1** | P2 (vol dampening) + P5 (confidence cal) | 2-3 hours | Quick wins, reduce large errors |
| **Week 2** | P1 (night session gap) + P4 (cross-market amp) | 4-6 hours | Major accuracy boost |
| **Week 3** | P3 (direction head overhaul) | 8-12 hours | Fundamental improvement |
| **Week 4** | P6 (weight decay) + re-backtest all | 3-4 hours | Fine-tuning |

---

## 6. Current Market Context (2026-03-27)

- Gold in extreme volatility regime (5-day vol 5.42%, annualized ~86%)
- COMEX experiencing overnight selloffs (night session consistently weaker)
- SHFE-COMEX premium widening (+12~23 CNY/g), domestic demand stronger
- Model predictions should be taken with LOW confidence in this regime
- Recommend reducing position sizing until vol normalizes (<30% annualized)
