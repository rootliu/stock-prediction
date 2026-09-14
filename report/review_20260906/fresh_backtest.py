import sys, time, json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ml-service'))
from models import multi_day_direct_predictor as m
OUT=Path(__file__).resolve().parent
data={n:pd.read_csv(OUT/'data'/f'{n}.csv',parse_dates=['date']) for n in ['shfe','comex','usdcny','cross']}
d=data['shfe'].sort_values('date').reset_index(drop=True)
for n,x in data.items():
    if x.empty: raise RuntimeError(f'Missing {n} data')
    if x.date.duplicated().any(): raise RuntimeError(f'Duplicate {n} dates')
records=[]
origins=list(range(max(260,len(d)-45),len(d)-5,5))
for variant in ['current','lag_external_1d','lag_external_no_router']:
    jump,trend=m._compute_jump_signal,m._compute_trend_reversal_signal
    if variant.endswith('no_router'):
        m._compute_jump_signal=lambda *a,**kw:(0.,0.)
        m._compute_trend_reversal_signal=lambda *a,**kw:(0.,0.)
    ext={k:v.copy() for k,v in data.items() if k!='shfe'}
    if variant!='current':
        for x in ext.values(): x['date']=x.date+pd.Timedelta(days=1)
    try:
        for oi in origins:
            origin=d.iloc[oi]; od=origin.date
            targets=list(d.iloc[oi+1:oi+6].date)
            t=time.time()
            preds=m.run_direct_multi_day_prediction(daily_df=d.iloc[:oi+1].copy(),comex_daily=ext['comex'][ext['comex'].date<=od],usdcny_daily=ext['usdcny'][ext['usdcny'].date<=od],cross_market=ext['cross'][ext['cross'].date<=od],target_dates=targets,lookback_days=240,verbose=False,horizons_to_train=[1,3,5])
            for p in preds:
                h=p.get('model_details',{}).get('horizon_days')
                if h not in [1,3,5]: continue
                actual=float(d.iloc[oi+int(h)].close)
                records.append(dict(variant=variant,origin_date=str(od.date()),target_date=str(d.iloc[oi+int(h)].date.date()),horizon=int(h),origin_close=float(origin.close),actual_close=actual,pred_close=p['close']))
            pd.DataFrame(records).to_csv(OUT/'fresh_predictions.csv',index=False)
            print(variant,str(od.date()),len(preds),round(time.time()-t,1),flush=True)
    finally:
        m._compute_jump_signal,m._compute_trend_reversal_signal=jump,trend
b=pd.DataFrame(records); rows=[]
for (v,h),g in b.groupby(['variant','horizon']):
    e=(g.pred_close-g.actual_close).abs(); be=(g.origin_close-g.actual_close).abs()
    rows.append(dict(variant=v,horizon=h,n=len(g),mae=e.mean(),baseline_mae=be.mean(),skill=1-e.mean()/be.mean(),direction_accuracy=(np.sign(g.pred_close-g.origin_close)==np.sign(g.actual_close-g.origin_close)).mean()*100))
s=pd.DataFrame(rows);s.to_csv(OUT/'fresh_summary.csv',index=False);print(s.to_string(index=False))
