#!/usr/bin/env python3
"""Read-only integrity checks plus a raw Kronos OHLC geometry diagnostic."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def audit(out):
    manifest = json.loads((out / 'manifest.json').read_text())
    for name, expected in manifest['code'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, f'Code changed: {name}'
    rows = []
    complete = 0
    for file in sorted((out / 'origins').glob('*.json')):
        record = json.loads(file.read_text())
        origin = record['origin_date']
        if 'fixed_gbm' in record:
            for horizon, prediction in record['fixed_gbm'].items():
                details = prediction['model_details']
                assert details['last_refit_label'] <= origin
                assert details['refit_size'] == 240
                assert prediction['date'] == record['targets'][horizon]['date'] > origin
                for source in details['external_observations'].values():
                    if source['last_available_at'] is not None:
                        assert pd.Timestamp(source['last_available_at']) <= pd.Timestamp(details['prediction_at'])
        if not all(name in record for name in ['legacy_aligned', 'fixed_gbm', 'kronos']):
            continue
        complete += 1
        path = out / 'paths' / f'{origin}.npz'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['kronos']['sha256']
        with np.load(path) as archive:
            values = archive['values']
            # Column order is fixed by the pinned producer/model. Its string
            # metadata has object dtype; validate numeric arrays without pickle.
            assert values.shape == (manifest['paths'], 5, 6)
            assert np.isfinite(values).all()
            assert int(archive['seed']) == int(origin.replace('-', '')) + 17
        invalid = ((values[:, :, 1] < np.maximum(values[:, :, 0], values[:, :, 3])) |
                   (values[:, :, 2] > np.minimum(values[:, :, 0], values[:, :, 3])) |
                   (values[:, :, 1] < values[:, :, 2]))
        for h in range(1, 6):
            rows.append({'origin_date': origin, 'horizon': h, 'evaluation': record['evaluation'],
                         'paths': manifest['paths'], 'invalid_ohlc': int(invalid[:, h-1].sum()),
                         'negative_volume': int((values[:, h-1, 4] < 0).sum()),
                         'nonpositive_close': int((values[:, h-1, 3] <= 0).sum())})
    quality = pd.DataFrame(rows)
    quality.to_csv(out / 'path_quality.csv', index=False)
    result = {'complete_origins': complete, 'expected_origins': manifest['origins'] + manifest['warmup'],
              'integrity_checks': 'passed', 'sampled_bars': int(quality.paths.sum()) if len(quality) else 0,
              'invalid_ohlc_bars': int(quality.invalid_ohlc.sum()) if len(quality) else 0,
              'note': 'OHLC violations are model-output diagnostics, not silently corrected or discarded.'}
    (out / 'audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', required=True)
    audit(Path(parser.parse_args().out_dir))
