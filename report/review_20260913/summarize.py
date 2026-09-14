"""Paired error comparisons on identical dates; block uncertainty and plots."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
variants = ['upstream', 'upstream_aligned', 'local']
frames = []
keys = ['origin_date', 'target_date', 'horizon']
for variant in variants:
    manifest = json.loads((OUT / f'{variant}_manifest.json').read_text())
    coverage = pd.read_csv(OUT / f'{variant}_coverage.csv')
    assert len(coverage) == 69 and coverage.error.isna().all()
    assert (coverage.expected == coverage.returned).all()
    frame = pd.read_csv(OUT / f'{variant}_predictions.csv')
    assert len(frame) == manifest['predictions'] == 261
    assert not frame.duplicated(keys).any()
    frames.append(frame)
reference = frames[0]
for frame in frames[1:]:
    pd.testing.assert_frame_equal(reference[keys + ['actual_close', 'origin_close']],
                                  frame[keys + ['actual_close', 'origin_close']])
daily = pd.read_csv(OUT / 'data/shfe.csv', parse_dates=['date'])
common_end = str(daily.iloc[-11].date.date())
base = reference.copy()
base['variant'] = 'persistence'
base['pred_close'] = base.origin_close
frames.append(base)
momentum = base.copy()
momentum['variant'] = 'momentum5'
daily['daily_log_drift5'] = np.log(daily.close / daily.close.shift(5)) / 5
drift = dict(zip(daily.date.dt.strftime('%Y-%m-%d'), daily.daily_log_drift5))
momentum['pred_close'] = momentum.origin_close * np.exp(momentum.origin_date.map(drift) * momentum.horizon)
frames.append(momentum)
all_data = pd.concat(frames, ignore_index=True)
all_data['abs_error'] = (all_data.pred_close - all_data.actual_close).abs()
all_data['baseline_error'] = (all_data.origin_close - all_data.actual_close).abs()
all_data['signed_error'] = all_data.pred_close - all_data.actual_close
all_data['direction_correct'] = (np.sign(all_data.pred_close-all_data.origin_close) == np.sign(all_data.actual_close-all_data.origin_close))
all_data.to_csv(OUT / 'all_predictions.csv', index=False)
windows = {
    'common_60_origins': all_data.origin_date <= common_end,
    'recent_2weeks': all_data.target_date >= '2026-08-31',
    'recent_week': all_data.target_date >= '2026-09-07',
}
rows = []
rng = np.random.default_rng(20260913)
for window, mask in windows.items():
    for (variant, horizon), group in all_data[mask].groupby(['variant', 'horizon']):
        group = group.sort_values('origin_date')
        delta = (group.abs_error-group.baseline_error).to_numpy()
        low = high = np.nan
        if window == 'common_60_origins':
            assert len(group) == 60
            n = len(delta)
            starts = rng.integers(0, n-10+1, size=(2000, int(np.ceil(n/10))))
            indexes = (starts[:, :, None] + np.arange(10)[None, None, :]).reshape(2000, -1)[:, :n]
            low, high = np.quantile(delta[indexes].mean(axis=1), [.025, .975])
        rows.append(dict(window=window, variant=variant, horizon=horizon, n=len(group),
            mae=group.abs_error.mean(), baseline_mae=group.baseline_error.mean(),
            skill_pct=100*(1-group.abs_error.mean()/group.baseline_error.mean()),
            mape_pct=(100*group.abs_error/group.actual_close).mean(),
            direction_pct=np.nan if variant=='persistence' else 100*group.direction_correct.mean(),
            signed_bias=group.signed_error.mean(), mae_delta=delta.mean(),
            delta_ci_low=low, delta_ci_high=high))
summary = pd.DataFrame(rows)
summary.to_csv(OUT / 'summary.csv', index=False)
all_data['month'] = all_data.target_date.str[:7]
monthly = all_data.groupby(['variant', 'horizon', 'month']).agg(n=('abs_error','size'),
    mae=('abs_error','mean'), baseline_mae=('baseline_error','mean'), signed_bias=('signed_error','mean')).reset_index()
monthly['skill_pct'] = 100*(1-monthly.mae/monthly.baseline_mae)
monthly.to_csv(OUT / 'monthly.csv', index=False)
guards = all_data[all_data.variant.isin(variants)].copy()
guards['pre_guard_price'] = guards.origin_close * (1 + guards.pre_guard_return_pct / 100)
guards['pre_guard_error'] = (guards.pre_guard_price-guards.actual_close).abs()
guards.groupby(['variant','horizon']).agg(n=('abs_error','size'),
    final_mae=('abs_error','mean'), pre_guard_mae=('pre_guard_error','mean')).to_csv(OUT/'guard_diagnostic.csv')

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
colors = ['#ad6570', '#daaa52', '#287d9b', '#333333', '#8888aa']
for ax, window, title in zip(axes, ['common_60_origins','recent_2weeks'],
                           ['60 common rolling origins', 'Targets: Aug 31 - Sep 11, 2026']):
    part = summary[summary.window == window]
    for index, (variant, color) in enumerate(zip(variants+['persistence','momentum5'], colors)):
        values = part[part.variant==variant].sort_values('horizon')
        ax.bar(np.arange(4)+(index-2)*.15, values.mae, width=.15, label=variant, color=color)
    ax.set_xticks(np.arange(4), ['T+1','T+3','T+5','T+10'])
    ax.set_ylabel('MAE (CNY / gram); lower is better')
    ax.set_title(title)
    ax.grid(axis='y', alpha=.2)
axes[0].legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT/'comparison.png', dpi=180)
print(summary.round(3).to_string(index=False))
