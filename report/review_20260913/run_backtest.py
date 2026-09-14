"""Fixed-snapshot rolling evaluation; no fitting on evaluation targets."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'ml-service'))
from models.market_availability import available_observations, daily_cutoff

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['upstream', 'upstream_aligned', 'local'], required=True)
    args = parser.parse_args()
    if args.variant == 'local':
        from models import multi_day_direct_predictor as model
        code = (ROOT / 'ml-service/models/multi_day_direct_predictor.py').read_bytes()
    else:
        code = subprocess.check_output(['git', 'show', '8418fad:ml-service/models/multi_day_direct_predictor.py'], cwd=ROOT)
        path = OUT / f'{args.variant}_source.py'
        path.write_bytes(code)
        spec = importlib.util.spec_from_file_location(args.variant, path)
        model = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model)
        if args.variant == 'upstream_aligned':
            original = model.build_cross_market_features
            def aligned(**kwargs):
                cutoff = daily_cutoff(kwargs['target_date'])
                for key in ['comex_daily', 'usdcny_daily', 'cross_market']:
                    kwargs[key] = available_observations(kwargs[key], cutoff)
                return original(**kwargs)
            model.build_cross_market_features = aligned
    data = {name: pd.read_csv(OUT / 'data' / f'{name}.csv', parse_dates=['date'])
            for name in ['shfe', 'comex', 'usdcny', 'cross']}
    daily = data['shfe'].sort_values('date').reset_index(drop=True)
    assert daily.date.max() <= pd.Timestamp('2026-09-11'), 'Incomplete/future daily bar'
    assert not daily.date.duplicated().any()
    assert (daily.low <= daily[['open', 'close']].min(axis=1)).all()
    assert (daily.high >= daily[['open', 'close']].max(axis=1)).all()
    horizons = (1, 3, 5, 10)
    origins = list(range(len(daily) - 10 - 60, len(daily) - 1))
    records, coverage = [], []
    started = time.monotonic()
    for oi in origins:
        row = daily.iloc[oi]
        future = daily.iloc[oi+1:oi+11]
        wanted = [h for h in horizons if h <= len(future)]
        tick = time.monotonic()
        try:
            ext = {n: data[n][data[n].date <= row.date].copy() for n in ['comex', 'usdcny', 'cross']}
            predictions = model.run_direct_multi_day_prediction(
                daily_df=daily.iloc[:oi+1].copy(), comex_daily=ext['comex'],
                usdcny_daily=ext['usdcny'], cross_market=ext['cross'],
                target_dates=list(future.date), lookback_days=240,
                horizons_to_train=wanted, verbose=False, cot_daily=None)
            returned = [int(p['model_details']['horizon_days']) for p in predictions]
            assert sorted(returned) == wanted, f'Missing/duplicate horizons {returned} != {wanted}'
            for prediction in predictions:
                h = int(prediction['model_details']['horizon_days'])
                target = future.iloc[h-1]
                assert pd.Timestamp(prediction['date']) == target.date
                price = float(prediction['close'])
                assert np.isfinite(price)
                records.append(dict(variant=args.variant, origin_date=str(row.date.date()),
                    target_date=str(target.date.date()), horizon=h, origin_close=float(row.close),
                    actual_close=float(target.close), pred_close=price,
                    confidence=prediction.get('confidence'),
                    pre_guard_return_pct=prediction['model_details'].get('pre_guard_return_pct'),
                    guard=prediction['model_details'].get('direction_guard')))
            coverage.append(dict(origin_date=str(row.date.date()), expected=len(wanted), returned=len(returned), error=None))
        except Exception as exc:
            coverage.append(dict(origin_date=str(row.date.date()), expected=len(wanted), returned=0, error=repr(exc)))
            raise
        finally:
            pd.DataFrame(records).to_csv(OUT / f'{args.variant}_predictions.csv', index=False)
            pd.DataFrame(coverage).to_csv(OUT / f'{args.variant}_coverage.csv', index=False)
        print(args.variant, len(coverage), '/', len(origins), row.date.date(), f'{time.monotonic()-tick:.1f}s', flush=True)
    manifest = dict(variant=args.variant, upstream_commit='8418fad', origins=len(origins),
        horizons=horizons, lookback=240, predictions=len(records), elapsed_seconds=time.monotonic()-started,
        model_sha256=hashlib.sha256(code).hexdigest(),
        data={n:hashlib.sha256((OUT/'data'/f'{n}.csv').read_bytes()).hexdigest() for n in data},
        source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__), ROOT/'ml-service/models/market_availability.py', ROOT/'ml-service/models/multi_bar_features.py']})
    (OUT / f'{args.variant}_manifest.json').write_text(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
