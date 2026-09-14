#!/usr/bin/env python3
"""Post-study path aggregation and probability-baseline diagnostics."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def diagnose(out):
    rows=[]
    for path in sorted((out/'origins').glob('*.json')):
        r=json.loads(path.read_text())
        if not r['evaluation'] or not all(k in r for k in ['legacy_aligned','fixed_gbm','kronos']):
            continue
        with np.load(out/'paths'/f"{r['origin_date']}.npz") as archive:
            closes=archive['values'][:,:,3]
        for h in [1,3,5]:
            values=closes[:,h-1];actual=r['targets'][str(h)]['actual']
            rows.append({'origin_date':r['origin_date'],'horizon':h,'actual':actual,'base':r['origin_close'],
                'mean':float(values.mean()),'median':float(np.median(values)),
                'q10':float(np.quantile(values,.1)),'q90':float(np.quantile(values,.9))})
    paths=pd.DataFrame(rows);paths.to_csv(out/'path_aggregation_predictions.csv',index=False)
    summary=[]
    for h,g in paths.groupby('horizon'):
        summary.append({'horizon':h,'n':len(g),'mean_mae':float((g['mean']-g.actual).abs().mean()),
            'median_mae':float((g['median']-g.actual).abs().mean()),'baseline_mae':float((g.base-g.actual).abs().mean()),
            'raw_interval_coverage80':float(((g.actual>=g.q10)&(g.actual<=g.q90)).mean()),
            'raw_interval_width':float((g.q90-g.q10).mean())})
    pd.DataFrame(summary).to_csv(out/'path_aggregation_summary.csv',index=False)
    predictions=pd.read_csv(out/'predictions.csv')
    base=predictions[predictions.variant=='fixed_gbm']
    baseline_rows=[]
    for current in predictions[(predictions.evaluation)&(predictions.variant.isin(['fixed_gbm','kronos']))].to_dict('records'):
        train=base[(base.horizon==current['horizon'])&(base.origin_date<current['origin_date'])&
                   (base.target_date<=current['origin_date'])]
        if len(train)<40 or pd.isna(current['calibrated_probability']): continue
        rate=float(((train.actual_return>0).sum()+1)/(len(train)+2))
        outcome=int(current['actual_return']>0)
        baseline_rows.append({'variant':current['variant'],'horizon':current['horizon'],
            'prior_brier':(rate-outcome)**2,'raw_brier':(current['raw_probability']-outcome)**2,
            'calibrated_brier':(current['calibrated_probability']-outcome)**2})
    b=pd.DataFrame(baseline_rows)
    b.groupby(['variant','horizon']).agg(n=('prior_brier','size'),prior_brier=('prior_brier','mean'),
        raw_brier=('raw_brier','mean'),calibrated_brier=('calibrated_brier','mean')).reset_index().to_csv(out/'probability_baselines.csv',index=False)
    print(pd.DataFrame(summary).round(4).to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out-dir',required=True)
    diagnose(Path(p.parse_args().out_dir))
