"""Fetch a new snapshot without modifying prior experiments."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import run_gold_analysis as source

out = Path(__file__).resolve().parent / 'data'
out.mkdir(parents=True, exist_ok=True)
manifest = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'data': {}}
for name, fn in [('shfe', source.fetch_shfe_au_daily),
                 ('comex', source.fetch_comex_daily),
                 ('usdcny', source.fetch_usdcny_daily),
                 ('cross', source.fetch_cross_market)]:
    frame = fn()
    assert not frame.empty and not frame.date.duplicated().any(), name
    if name == 'cross':
        assert all(c in frame and frame[c].notna().sum() > 500 for c in ['dxy', 'vix', 'us10y'])
    path = out / f'{name}.csv'
    frame.to_csv(path, index=False)
    manifest['data'][name] = dict(rows=len(frame), start=str(frame.date.min()),
        end=str(frame.date.max()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print(name, manifest['data'][name], flush=True)
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
