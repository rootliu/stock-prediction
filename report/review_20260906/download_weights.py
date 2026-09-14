"""Download the exact official checkpoints used for this experiment."""
import argparse
from pathlib import Path
from huggingface_hub import hf_hub_download

parser = argparse.ArgumentParser()
parser.add_argument('--weights-dir', default='/tmp/gold-kronos-weights')
args = parser.parse_args()
for name, repo, revision in [
    ('tokenizer', 'NeoQuasar/Kronos-Tokenizer-base', '0e0117387f39004a9016484a186a908917e22426'),
    ('small', 'NeoQuasar/Kronos-small', '901c26c1332695a2a8f243eb2f37243a37bea320'),
]:
    for filename in ['config.json', 'model.safetensors']:
        hf_hub_download(repo_id=repo, filename=filename, revision=revision,
                        local_dir=Path(args.weights_dir)/name)
