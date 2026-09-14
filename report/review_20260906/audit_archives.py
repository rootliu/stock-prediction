from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
rows=[]
for filename in ['gold_continuation_backtest_2026-05-28_to_2026-06-18.csv', 'gold_continuation_backtest_2026-08-21_to_2026-09-04.csv']:
    d=pd.read_csv(ROOT/'report'/filename)
    assert not d.duplicated(['origin_date','target_date','horizon']).any()
    for h,g in d.groupby('horizon'):
        base=np.abs(g.actual_close-g.origin_close).mean()
        for name,pred in [('direct',g.pred_close),('persistence',g.origin_close),('shrink_50',g.origin_close+0.5*(g.pred_close-g.origin_close))]:
            e=np.abs(pred-g.actual_close)
            rows.append(dict(window=filename,model=name,horizon=int(h),n=len(g),mae=e.mean(),mape=(e/g.actual_close).mean()*100,skill_vs_persistence=1-e.mean()/base,direction_accuracy=(np.sign(pred-g.origin_close)==np.sign(g.actual_close-g.origin_close)).mean()*100))
pd.DataFrame(rows).to_csv(OUT/'archive_comparison.csv',index=False)
print(pd.DataFrame(rows).round(3).to_string(index=False))
