#!/usr/bin/env python3
"""Build monthly matched-origin evaluations and online calibration diagnostics."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ml-service'))
from models.kronos_combination import predict_combination, calibrated_probability, calibrated_radius


def summarize(out):
    manifest=json.loads((out/'manifest.json').read_text())
    rows=[];coverage=[]
    for file in sorted((out/'origins').glob('*.json')):
        r=json.loads(file.read_text())
        valid=all(k in r for k in ['legacy_aligned','fixed_gbm','kronos'])
        coverage.append({'origin_date':r['origin_date'],'evaluation':r['evaluation'],'complete':valid,
                         **{name:name in r for name in ['legacy_aligned','fixed_gbm','kronos']}})
        if not valid: continue
        import hashlib
        path=out/'paths'/f"{r['origin_date']}.npz"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=r['kronos']['sha256']:
            raise ValueError(f'Path checkpoint changed: {path}')
        values=np.load(path)['values'][:,:,3]
        for h in [1,3,5]:
            base=r['origin_close'];returns=values[:,h-1]/base-1
            p=r['fixed_gbm'][str(h)]
            gbm=p['close']/base-1;kr=float(returns.mean())
            rows.append(dict(origin_date=r['origin_date'],target_date=r['targets'][str(h)]['date'],horizon=h,
                origin_close=base,actual_close=r['targets'][str(h)]['actual'],
                actual_return=r['targets'][str(h)]['actual']/base-1,evaluation=r['evaluation'],
                gbm_return=gbm,legacy_return=r['legacy_aligned'][str(h)]['close']/base-1,
                kronos_return=kr,path_std=float(returns.std()),path_up_fraction=float((returns>0).mean()),
                path_q10=float(np.quantile(returns,.1)),path_q90=float(np.quantile(returns,.9)),
                disagreement=kr-gbm,vol20=r['vol20'],gbm_probability=p['model_details'].get('up_probability')))
    c=pd.DataFrame(coverage);c.to_csv(out/'coverage.csv',index=False)
    if not rows: raise ValueError('No complete common origins')
    data=pd.DataFrame(rows).sort_values(['origin_date','horizon']).reset_index(drop=True)
    outputs=[];histories={}
    for current in data.to_dict('records'):
        # All routines additionally filter maturity, including multi-day labels.
        predictions={'persistence':0.,'legacy_aligned':current['legacy_return'],
                     'fixed_gbm':current['gbm_return'],'kronos':current['kronos_return'],
                     'meta_gbm':predict_combination(data,current,False),
                     'meta_kronos':predict_combination(data,current,True)}
        kp=calibrated_probability(data,current,'path_up_fraction')
        gp=calibrated_probability(data,current,'gbm_probability')
        for variant,pred in predictions.items():
            prior=pd.DataFrame(histories.get(variant,[]))
            radius,n=calibrated_radius(prior,current['origin_date'],current['horizon'])
            row={**current,'variant':variant,'pred_return':pred,
                 'pred_close':current['origin_close']*(1+pred),'calibration_samples':n,
                 'range_low':None if radius is None else current['origin_close']*(1+pred-radius),
                 'range_high':None if radius is None else current['origin_close']*(1+pred+radius),
                 'raw_probability':current['path_up_fraction'] if variant=='kronos' else (current['gbm_probability'] if variant=='fixed_gbm' else None),
                 'calibrated_probability':kp if variant=='kronos' else (gp if variant=='fixed_gbm' else None)}
            histories.setdefault(variant,[]).append(row);outputs.append(row)
    result=pd.DataFrame(outputs);result.to_csv(out/'predictions.csv',index=False)
    scored=result[result.evaluation].copy()
    scored['month']=pd.to_datetime(scored.target_date).dt.to_period('M').astype(str)
    def metrics(g):
        error=(g.pred_close-g.actual_close).abs();base=(g.origin_close-g.actual_close).abs().mean()
        intervals=g.dropna(subset=['range_low','range_high'])
        prob=g.dropna(subset=['calibrated_probability','raw_probability'])
        return dict(n=len(g),mae=error.mean(),baseline_mae=base,skill=1-error.mean()/base if base else np.nan,
            direction_accuracy=np.nan if g.variant.iloc[0]=='persistence' else float((np.sign(g.pred_return)==np.sign(g.actual_return)).mean()),
            interval_n=len(intervals),coverage80=float(((intervals.actual_close>=intervals.range_low)&(intervals.actual_close<=intervals.range_high)).mean()),
            interval_width=float((intervals.range_high-intervals.range_low).mean()),probability_n=len(prob),
            raw_brier=float(((prob.raw_probability-(prob.actual_return>0).astype(int))**2).mean()),
            calibrated_brier=float(((prob.calibrated_probability-(prob.actual_return>0).astype(int))**2).mean()))
    summary=pd.DataFrame([{'variant':v,'horizon':h,**metrics(g)} for (v,h),g in scored.groupby(['variant','horizon'])])
    monthly=pd.DataFrame([{'month':month,'variant':v,'horizon':h,**metrics(g)} for (month,v,h),g in scored.groupby(['month','variant','horizon'])])
    summary.to_csv(out/'summary.csv',index=False);monthly.to_csv(out/'monthly.csv',index=False)
    # Moving blocks preserve short-range dependence between adjacent origins.
    rng=np.random.default_rng(42);ci=[]
    for h in [1,3,5]:
        left=scored[(scored.variant=='meta_gbm')&(scored.horizon==h)].set_index('origin_date')
        right=scored[(scored.variant=='meta_kronos')&(scored.horizon==h)].set_index('origin_date')
        if len(left)<20: continue
        difference=((right.pred_close-right.actual_close).abs()-(left.pred_close-left.actual_close).abs()).sort_index().to_numpy()
        n=len(difference);block=10;boot=[]
        for _ in range(1000):
            starts=rng.integers(0,n-block+1,size=int(np.ceil(n/block)))
            indices=np.concatenate([np.arange(s,s+block) for s in starts])[:n]
            boot.append(difference[indices].mean())
        ci.append(dict(horizon=h,n=n,mae_delta= float(difference.mean()),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),block=block))
    pd.DataFrame(ci).to_csv(out/'paired_bootstrap.csv',index=False)
    expected=manifest['origins'];completed=int(c[c.evaluation].complete.sum()) if len(c) else 0
    table=summary.pivot(index='variant',columns='horizon',values='mae').round(3).to_markdown()
    text=f'''# Gold research result\n\nEvaluation origins completed: {completed}/{expected}; warmup: {manifest['warmup']}.\n\n{table}\n\n- All metrics use common complete origins; coverage.csv lists missing stages.\n- Labels enter meta-model/calibration training only once target_date <= current origin.\n- Meta models use fixed Ridge alpha=10 and >=40 matured observations. No test-period hyperparameter selection.\n- Intervals use up to 120 prior matured absolute return errors (nominal 80%); temporal dependence means coverage is empirical, not guaranteed.\n- Probability calibration is logistic on prior matured labels; compare raw/calibrated Brier on identical samples.\n- paired_bootstrap.csv compares meta_kronos minus meta_gbm MAE, using 10-origin moving blocks and 1000 resamples. Negative favors Kronos features.\n- This is retrospective research, not a sealed prospective test; original guards were developed using some overlapping historical dates.\n- Date-only external observations use an explicit assumed availability time, not verified provider publication timestamps.\n- No production selector is changed automatically.\n'''
    (out/'RESULTS.md').write_text(text)
    print(summary[['variant','horizon','n','mae','skill']].round(4).to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out-dir',required=True)
    summarize(Path(p.parse_args().out_dir))
