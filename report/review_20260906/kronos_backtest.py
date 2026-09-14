"""Official Kronos-small zero-shot diagnostic; no project integration implied."""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

parser = argparse.ArgumentParser()
parser.add_argument('--kronos-dir', default='/tmp/gold-kronos-official')
parser.add_argument('--weights-dir', default='/tmp/gold-kronos-weights')
parser.add_argument('--lookback', type=int, default=240, choices=[128,240])
args = parser.parse_args()
sys.path.insert(0, args.kronos_dir)
from model import Kronos, KronosTokenizer, KronosPredictor

BASE = Path(__file__).resolve().parent
OUT = BASE if args.lookback == 240 else BASE / 'context128'
OUT.mkdir(exist_ok=True)
torch.set_num_threads(2)
torch.set_num_interop_threads(2)
tokenizer = KronosTokenizer.from_pretrained(str(Path(args.weights_dir) / 'tokenizer'))
model = Kronos.from_pretrained(str(Path(args.weights_dir) / 'small'))
tokenizer.eval()
model.eval()
predictor = KronosPredictor(model, tokenizer, device='cpu', max_context=512)
d = pd.read_csv(BASE / 'data/shfe.csv', parse_dates=['date']).sort_values('date').reset_index(drop=True)
origins = pd.read_csv(BASE / 'fresh_predictions.csv').origin_date.unique()
rows = []
for date in origins:
    oi = int(d.index[d.date == pd.Timestamp(date)][0])
    history = d.iloc[oi-args.lookback+1:oi+1].reset_index(drop=True)
    future = d.iloc[oi+1:oi+6].reset_index(drop=True)
    assert len(history) == args.lookback and len(future) == 5
    assert history.date.max() < future.date.min()
    x = history[['open', 'high', 'low', 'close', 'volume']].astype(float)
    assert np.isfinite(x.to_numpy()).all()
    # No turnover field in source: official predictor estimates amount from OHLC mean * volume.
    for seed in [17, 29, 43]:
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        started = time.time()
        pred = predictor.predict(x, history.date, future.date, pred_len=5,
                                 T=1.0, top_p=0.9, sample_count=8, verbose=False)
        assert len(pred) == 5 and np.isfinite(pred.close.to_numpy()).all()
        for h in [1, 3, 5]:
            rows.append(dict(origin_date=date, target_date=str(future.iloc[h-1].date.date()),
                             horizon=h, seed=seed, origin_close=float(history.iloc[-1].close),
                             actual_close=float(future.iloc[h-1].close), pred_close=float(pred.iloc[h-1].close)))
        pd.DataFrame(rows).to_csv(OUT / 'kronos_seed_predictions.csv', index=False)
        print(date, seed, round(time.time()-started, 2), flush=True)

all_rows = pd.DataFrame(rows)
ensemble = all_rows.groupby(['origin_date', 'target_date', 'horizon', 'origin_close', 'actual_close'], as_index=False).agg(pred_close=('pred_close', 'mean'), seed_mean_std=('pred_close', 'std'))
ensemble.to_csv(OUT / 'kronos_predictions.csv', index=False)
summary = []
for label, frame in [(f'seed_{seed}', all_rows[all_rows.seed == seed]) for seed in [17,29,43]] + [('ensemble_24_paths', ensemble)]:
    for h, g in frame.groupby('horizon'):
        error = (g.pred_close-g.actual_close).abs()
        baseline = (g.origin_close-g.actual_close).abs().mean()
        summary.append(dict(variant=label, horizon=int(h), n=len(g), mae=error.mean(),
                            baseline_mae=baseline, skill=1-error.mean()/baseline,
                            direction_accuracy=(np.sign(g.pred_close-g.origin_close)==np.sign(g.actual_close-g.origin_close)).mean()*100))
s = pd.DataFrame(summary)
s.to_csv(OUT / 'kronos_summary.csv', index=False)
print(s.to_string(index=False))
