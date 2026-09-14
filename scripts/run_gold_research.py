#!/usr/bin/env python3
"""Resumable, fixed-snapshot gold study. No network access or automatic deployment.

Each origin is atomically checkpointed. Restart with identical arguments/code;
already completed work is skipped. A process lock prevents duplicate workers.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))
from models import multi_day_direct_predictor as fixed
from models.market_availability import available_observations, daily_cutoff

HORIZONS = (1, 3, 5)


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_features(module):
    # Scope is one immutable data snapshot and one module/timing policy. Features
    # already filter by their own origin; no future-derived values enter the key.
    original = module._build_direct_feature_row
    cache = {}
    def cached(**kwargs):
        key = (str(kwargs['current_date']), kwargs['horizon_days'],
               str(daily_cutoff(kwargs['current_date'], kwargs.get('prediction_at'))))
        if key not in cache:
            cache[key] = original(**kwargs)
        return dict(cache[key])
    module._build_direct_feature_row = cached


def load_legacy(out):
    code = subprocess.check_output(['git', 'show', 'c74f7d2:ml-service/models/multi_day_direct_predictor.py'], cwd=ROOT)
    path = out / f'legacy_source_{os.getpid()}.py'
    path.write_bytes(code)
    spec = importlib.util.spec_from_file_location('gold_legacy', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.build_cross_market_features
    def aligned(**kwargs):
        cutoff = daily_cutoff(kwargs['target_date'])
        for key in ['comex_daily', 'usdcny_daily', 'cross_market']:
            kwargs[key] = available_observations(kwargs[key], cutoff)
        return original(**kwargs)
    module.build_cross_market_features = aligned
    cache_features(module)
    return module


def run_gbm(module, history, data, future):
    predictions = module.run_direct_multi_day_prediction(
        daily_df=history, comex_daily=data['comex'], usdcny_daily=data['usdcny'],
        cross_market=data['cross'], target_dates=list(future.date),
        lookback_days=240, horizons_to_train=HORIZONS, verbose=False)
    result = {}
    for p in predictions:
        h = int(p['model_details']['horizon_days'])
        if p['date'] != str(future.iloc[h-1].date.date()):
            raise ValueError('Horizon/date mismatch')
        result[str(h)] = p
    if set(result) != {'1','3','5'}:
        raise ValueError('Missing horizon')
    return result


def load_kronos(args):
    sys.path.insert(0, str(Path(args.kronos_dir).resolve()))
    import torch
    from model import Kronos, KronosTokenizer, KronosPredictor
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    tokenizer = KronosTokenizer.from_pretrained(str(Path(args.weights_dir)/'tokenizer'))
    model = Kronos.from_pretrained(str(Path(args.weights_dir)/'small'))
    tokenizer.eval(); model.eval()
    return KronosPredictor(model, tokenizer, device='cpu', max_context=512)


def run_paths(predictor, history, future, args, path):
    import torch
    seed = int(history.iloc[-1].date.strftime('%Y%m%d')) + 17
    np.random.seed(seed); torch.manual_seed(seed)
    history = history.tail(240).reset_index(drop=True)
    future = future.reset_index(drop=True)
    x = history[['open','high','low','close','volume']].astype(float)
    # Separate batch members + sample_count=1 retain every sampled trajectory.
    forecasts = predictor.predict_batch([x]*args.paths, [history.date]*args.paths,
        [future.date]*args.paths, pred_len=5, T=1.0, top_p=.9, sample_count=1, verbose=False)
    values = np.stack([f.to_numpy() for f in forecasts])
    if values.shape != (args.paths,5,6) or not np.isfinite(values).all():
        raise ValueError('Invalid Kronos trajectories')
    with path.with_suffix('.tmp').open('wb') as handle:
        np.savez_compressed(handle, values=values, columns=np.array(forecasts[0].columns), seed=seed)
        handle.flush(); os.fsync(handle.fileno())
    path.with_suffix('.tmp').replace(path)
    return {'seed':seed, 'paths':args.paths, 'sha256':fingerprint(path)}


def parse_args():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default=str(ROOT/'report/review_20260906/data'))
    p.add_argument('--out-dir',default=str(ROOT/'analysis_outputs/gold_research_v1'))
    p.add_argument('--origins',type=int,default=200,help='Evaluation origins after warmup')
    p.add_argument('--warmup',type=int,default=80,help='Earlier origins for combination/calibration fitting')
    p.add_argument('--paths',type=int,default=8)
    p.add_argument('--kronos-dir',default='/tmp/gold-kronos-official')
    p.add_argument('--weights-dir',default='/tmp/gold-kronos-weights')
    p.add_argument('--phase',choices=['all','gbm','kronos','summarize'],default='all')
    p.add_argument('--workers',type=int,default=1,help='Independent numeric worker processes (not coding agents)')
    p.add_argument('--shard-index',type=int,default=None,help=argparse.SUPPRESS)
    return p.parse_args()


def main():
    args=parse_args()
    if min(args.origins,args.paths) < 1 or args.warmup < 0:
        raise ValueError('Invalid origin/path counts')
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    if args.workers < 1 or args.workers > 8:
        raise ValueError('workers must be between 1 and 8')
    shard=args.shard_index
    if shard is not None and not 0 <= shard < args.workers:
        raise ValueError('Invalid shard index')
    lock=(out/('worker.lock' if shard is None else f'worker.{shard}.lock')).open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('A worker already holds this study lock')
    data={name:pd.read_csv(Path(args.data_dir)/f'{name}.csv',parse_dates=['date'])
          for name in ['shfe','comex','usdcny','cross']}
    daily=data['shfe'].sort_values('date').reset_index(drop=True)
    if daily.date.duplicated().any() or daily.empty:
        raise ValueError('Invalid SHFE calendar')
    total=args.origins+args.warmup
    origins=list(range(len(daily)-5-total,len(daily)-5))
    if origins[0]<260: raise ValueError('Insufficient history')
    source_files=[Path(__file__), ROOT/'scripts/summarize_gold_research.py',
                  *[ROOT/'ml-service/models'/name for name in
                    ['multi_day_direct_predictor.py','market_availability.py','multi_bar_features.py','volatility_regime.py','kronos_combination.py']]]
    configuration={'origins':args.origins,'warmup':args.warmup,'paths':args.paths,'horizons':HORIZONS,
        'data':{n:fingerprint(Path(args.data_dir)/f'{n}.csv') for n in data},
        'code':{str(p.relative_to(ROOT)):fingerprint(p) for p in source_files},
        'weights':{str(p.relative_to(Path(args.weights_dir))):fingerprint(p) for p in sorted(Path(args.weights_dir).glob('*/*')) if p.suffix in ['.safetensors','.json']},
        'packages':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scikit-learn','torch','huggingface_hub']},
        'kronos_code':{str(p.relative_to(Path(args.kronos_dir))):fingerprint(p) for p in sorted((Path(args.kronos_dir)/'model').glob('*.py'))},
        'first_origin':str(daily.iloc[origins[0]].date.date()),'last_origin':str(daily.iloc[origins[-1]].date.date()),
        'first_evaluation_origin':str(daily.iloc[origins[args.warmup]].date.date()),
        'external_policy':'explicit available_at else next-calendar-day 08:00 Asia/Shanghai',
        'kronos':{'context':240,'T':1.,'top_p':.9,'sample_count':1,'seed':'YYYYMMDD + 17'},
        'note':'Exploratory historical study; date-only market publication times are assumed.'}
    configuration=json.loads(json.dumps(configuration))
    manifest=out/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text()) != configuration:
            raise ValueError('Study code/data/config changed; use a new output directory')
    else:
        atomic_json(manifest,configuration)
    for name in ['origins','paths']: (out/name).mkdir(exist_ok=True)
    if args.phase=='summarize':
        subprocess.run([sys.executable,str(ROOT/'scripts/summarize_gold_research.py'),'--out-dir',str(out)],check=True)
        return
    if args.workers > 1 and shard is None:
        children=[]
        for index in range(args.workers):
            atomic_json(out/f'status.{index}.json',{'state':'starting','processed':0,'total':0})
            command=[sys.executable,str(Path(__file__).resolve()),'--data-dir',args.data_dir,
                '--out-dir',str(out),'--origins',str(args.origins),'--warmup',str(args.warmup),
                '--paths',str(args.paths),'--kronos-dir',args.kronos_dir,'--weights-dir',args.weights_dir,
                '--phase',args.phase,'--workers',str(args.workers),'--shard-index',str(index)]
            children.append(subprocess.Popen(command))
        while any(child.poll() is None for child in children):
            statuses=[]
            for index in range(args.workers):
                path=out/f'status.{index}.json'
                if path.exists(): statuses.append(json.loads(path.read_text()))
            atomic_json(out/'status.json',{'state':'running','workers':args.workers,'total':total,
                'processed':sum(s['processed'] for s in statuses),'shards':statuses,
                'updated_at':pd.Timestamp.now(tz='UTC').isoformat()})
            time.sleep(5)
        failed=[i for i,child in enumerate(children) if child.returncode]
        if args.phase=='all':
            subprocess.run([sys.executable,str(ROOT/'scripts/summarize_gold_research.py'),'--out-dir',str(out)],check=True)
        atomic_json(out/'status.json',{'state':'failed' if failed else 'complete','processed':total,
            'total':total,'failed_workers':failed,'updated_at':pd.Timestamp.now(tz='UTC').isoformat()})
        if failed: raise SystemExit(1)
        return
    legacy=load_legacy(out) if args.phase in ['all','gbm'] else None
    cache_features(fixed)
    predictor=load_kronos(args) if args.phase in ['all','kronos'] else None
    failures=[]
    assigned=list(enumerate(origins))
    if shard is not None:
        assigned=[tuple(map(int,pair)) for pair in np.array_split(np.array(assigned),args.workers)[shard]]
    status_path=out/('status.json' if shard is None else f'status.{shard}.json')
    for processed,(number,oi) in enumerate(assigned,start=1):
        origin=str(daily.iloc[oi].date.date());checkpoint=out/'origins'/f'{origin}.json'
        record=json.loads(checkpoint.read_text()) if checkpoint.exists() else {
            'origin_date':origin,'origin_close':float(daily.iloc[oi].close),'evaluation':number>=args.warmup,
            'targets':{str(h):{'date':str(daily.iloc[oi+h].date.date()),'actual':float(daily.iloc[oi+h].close)} for h in HORIZONS}}
        history=daily.iloc[:oi+1].copy();future=daily.iloc[oi+1:oi+6]
        record['vol20']=float(history.close.pct_change().tail(20).std())
        atomic_json(checkpoint,record)
        for name,module in [('legacy_aligned',legacy),('fixed_gbm',fixed if legacy else None)]:
            if module is None or name in record: continue
            try:
                start=time.time();record[name]=run_gbm(module,history,data,future)
                atomic_json(checkpoint,record)
                print(origin,name,round(time.time()-start,2),'s',flush=True)
            except Exception as exc:
                failures.append({'origin':origin,'stage':name,'error':repr(exc)})
                traceback.print_exc()
        if predictor is not None and 'kronos' not in record:
            try:
                start=time.time();record['kronos']=run_paths(predictor,history,future,args,out/'paths'/f'{origin}.npz')
                atomic_json(checkpoint,record)
                print(origin,'kronos',round(time.time()-start,2),'s',flush=True)
            except Exception as exc:
                failures.append({'origin':origin,'stage':'kronos','error':repr(exc)})
                traceback.print_exc()
        atomic_json(status_path,{'state':'running','phase':args.phase,'processed':processed,'total':len(assigned),
                    'last_origin':origin,'failures':failures,'updated_at':pd.Timestamp.now(tz='UTC').isoformat()})
    atomic_json(status_path,{'state':'failed' if failures else 'computed','phase':args.phase,
                'processed':len(assigned),'total':len(assigned),'failures':failures,'updated_at':pd.Timestamp.now(tz='UTC').isoformat()})
    if args.phase=='all' and shard is None:
        subprocess.run([sys.executable,str(ROOT/'scripts/summarize_gold_research.py'),'--out-dir',str(out)],check=True)
    if failures: raise SystemExit(1)
    atomic_json(status_path,{'state':'complete','phase':args.phase,'processed':len(assigned),'total':len(assigned),
                'failures':[],'updated_at':pd.Timestamp.now(tz='UTC').isoformat()})


if __name__=='__main__':
    main()
