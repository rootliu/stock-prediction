import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import run_gold_analysis as r
r._retry=lambda fn, **kwargs: fn()
out=Path(__file__).resolve().parent / 'data'; out.mkdir(parents=True,exist_ok=True)
for name, fn in [('shfe',r.fetch_shfe_au_daily),('comex',r.fetch_comex_daily),('usdcny',r.fetch_usdcny_daily),('cross',r.fetch_cross_market)]:
    try:
        df=fn(); df.to_csv(out/f'{name}.csv',index=False)
        print(name,len(df),flush=True)
    except Exception as e:
        print(name,type(e).__name__,str(e),flush=True)
