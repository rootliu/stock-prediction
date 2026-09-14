#!/usr/bin/env python3
"""Diagnose historical-only tokenizer reconstruction; no forecast adjustment."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out-dir',required=True)
    parser.add_argument('--kronos-dir',default='/tmp/gold-kronos-official')
    parser.add_argument('--weights-dir',default='/tmp/gold-kronos-weights')
    args=parser.parse_args();out=Path(args.out_dir)
    sys.path.insert(0,args.kronos_dir)
    from model import KronosTokenizer
    torch.set_num_threads(2)
    tokenizer=KronosTokenizer.from_pretrained(str(Path(args.weights_dir)/'tokenizer')).eval()
    data=pd.read_csv(ROOT/'report/review_20260906/data/shfe.csv',parse_dates=['date'])
    rows=[]
    for file in sorted((out/'origins').glob('*.json')):
        record=json.loads(file.read_text())
        if not record['evaluation']: continue
        history=data[data.date<=record['origin_date']].tail(240)
        x=history[['open','high','low','close','volume']].astype(float).copy()
        x['amount']=x[['open','high','low','close']].mean(axis=1)*x.volume
        values=x.to_numpy(dtype=np.float32);mean=values.mean(axis=0);std=values.std(axis=0)
        norm=(values-mean)/(std+1e-5)
        with torch.no_grad():
            tokens=tokenizer.encode(torch.from_numpy(np.clip(norm,-5,5)[None]),half=True)
            reconstructed=tokenizer.decode(tokens,half=True).numpy()[0]*(std+1e-5)+mean
        rows.append({'origin_date':record['origin_date'],'actual_last_close':float(values[-1,3]),
                     'reconstructed_last_close':float(reconstructed[-1,3]),
                     'last_close_z':float(norm[-1,3]),
                     'reconstruction_error':float(reconstructed[-1,3]-values[-1,3]),
                     'clipped_input_fraction':float((np.abs(norm)>5).mean())})
    result=pd.DataFrame(rows);result.to_csv(out/'tokenizer_reconstruction.csv',index=False)
    result['month']=pd.to_datetime(result.origin_date).dt.to_period('M').astype(str)
    monthly=result.groupby('month').agg(n=('origin_date','size'),mean_error=('reconstruction_error','mean'),
        mae=('reconstruction_error',lambda x:x.abs().mean()),max_abs_z=('last_close_z',lambda x:x.abs().max()))
    monthly.to_csv(out/'tokenizer_reconstruction_monthly.csv')
    print(monthly.round(3).to_string())


if __name__=='__main__':main()
