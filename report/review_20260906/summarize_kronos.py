"""Compare fixed diagnostic mixtures on exactly matched origin/horizon keys."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
g=pd.read_csv(OUT/'fresh_predictions.csv')
k=pd.read_csv(OUT/'kronos_predictions.csv')
keys=['origin_date','target_date','horizon','origin_close','actual_close']
assert len(k)==24 and not k.duplicated(keys).any()
lag=g[g.variant=='lag_external_1d'].drop(columns='variant')
joined=lag.merge(k,on=keys,suffixes=('_gbm','_kronos'),validate='one_to_one')
assert len(joined)==len(lag)==len(k)
rows=[]; predictions=[]
for name, p in [('Persistence',joined.origin_close),('GBM lag 1d',joined.pred_close_gbm),('Kronos small',joined.pred_close_kronos),('25% Kronos',.75*joined.pred_close_gbm+.25*joined.pred_close_kronos),('50% Kronos',.5*joined.pred_close_gbm+.5*joined.pred_close_kronos)]:
    result=joined[keys].copy();result['pred_close']=p;result['variant']=name
    predictions.append(result)
    for h,sub in result.groupby('horizon'):
        e=(sub.pred_close-sub.actual_close).abs(); b=(sub.origin_close-sub.actual_close).abs().mean()
        rows.append(dict(variant=name,horizon=h,n=len(sub),mae=e.mean(),baseline_mae=b,skill=1-e.mean()/b,direction_accuracy=np.nan if name=='Persistence' else (np.sign(sub.pred_close-sub.origin_close)==np.sign(sub.actual_close-sub.origin_close)).mean()*100))
s=pd.DataFrame(rows);s.to_csv(OUT/'combined_summary.csv',index=False)
pd.concat(predictions).to_csv(OUT/'combined_predictions.csv',index=False)
pivot=s.pivot(index='horizon',columns='variant',values='mae')
ax=pivot.plot.bar(figsize=(9,4.8),rot=0,color=['#a855f7','#c084fc','#2563eb','#f59e0b','#64748b'])
ax.set(xlabel='Forecast horizon (trading days)',ylabel='MAE (CNY / gram)',title='Gold: matched-origin diagnostic backtest (8 origins)')
ax.legend(loc='upper left',fontsize=8)
ax.grid(axis='y',alpha=.2);plt.tight_layout();plt.savefig(OUT/'comparison.png',dpi=180);plt.close()
print(s.round(4).to_string(index=False))
