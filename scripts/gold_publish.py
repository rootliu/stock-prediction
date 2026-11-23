"""Single-writer, append-only direct forecast bundles; manifest is the commit marker."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {"report_md": "report.md", "report_txt": "report.txt", "scenario_png": "scenario.png",
           "scenario_csv": "scenario.csv", "scenario_json": "scenario.json"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as fh:
        fh.write(data)
    os.replace(fh.name, path)


def encoded(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False).encode()


def history_key(options):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--lookback", type=int, default=240)
    args, _ = parser.parse_known_args(options)
    files = ["multi_day_direct_predictor", "multi_bar_features", "direction_confidence",
             "market_availability", "volatility_regime", "gold_feed"]
    digest = hashlib.sha256(encoded([args.lookback, os.getenv("GOLD_DIRECTION_CONFIDENCE_MODE", "calibrated")]))
    for name in files:
        digest.update((ROOT / "ml-service/models" / (name + ".py")).read_bytes())
    return digest.hexdigest()


def issue(folder, target=None, options=(), runner=subprocess.run):
    folder = Path(folder).resolve()
    folder.mkdir(exist_ok=True, parents=True)
    with (folder / ".publish.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
        run = folder / "runs" / run_id
        run.mkdir(parents=True)
        manifest = dict(report_type="gold_direct_v3", status="running", run_id=run_id, files={},
                        target_end=target, started_at=timestamp(), delivery="unconfirmed")
        atomic(folder / "manifest.json", encoded(manifest))
        log = run / "report.txt"
        paths = {"report_txt": log}
        try:
            import pandas as pd
            sys.path.insert(0, str(ROOT / "ml-service"))
            from models.gold_feed import target_after, expected
            target = target or target_after(expected(pd.Timestamp.now(tz="Asia/Shanghai"), "shfe"))
            if "--skip-cross-market" in options:
                raise ValueError("正式 direct 报告需要全部跨市场输入；仅诊断时请去掉 --report-dir")
            if pd.Timestamp(target).year != 2026:
                raise ValueError("目标年份未配置正式交易日历")
            manifest["target_end"] = target
            manifest["git_commit"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                                             text=True).strip()
            manifest["model_options"] = list(options)
            manifest["history_key"] = history_key(options)
            cmd = [sys.executable, str(ROOT / "run_gold_analysis.py"), *options, "--forecast-mode", "direct",
                   "--target-end", target, "--report-dir", str(run)]
            env = dict(os.environ, GOLD_DIRECT_CHILD="1", GOLD_RUN_HISTORY=str(folder / "runs"),
                       GOLD_HISTORY_KEY=manifest["history_key"])
            with log.open("w") as fh:
                result = runner(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, timeout=1800)
            if result.returncode:
                raise RuntimeError(log.read_text(errors="replace").strip().splitlines()[-1][:1000]
                                   if log.stat().st_size else f"model exit {result.returncode}")
            (scenario,) = run.glob("gold_direct_scenario_*.json")
            bundle = json.loads(scenario.read_text())
            if not bundle.get("predictions") or set(bundle.get("input_data") or {}) != {"shfe", "comex", "usdcny", "cross"}:
                raise ValueError("缺少预测或行情来源")
            products = {key: scenario.with_suffix(Path(alias).suffix) for key, alias in ALIASES.items()
                        if key != "report_txt"}
            if not all(path.is_file() and path.stat().st_size for path in products.values()):
                raise ValueError("预测附件不完整")
            paths.update(products)
            manifest.update(status="ok", origin=bundle["latest_date"], model="direct/v1",
                            input_data=bundle["input_data"])
        except Exception as exc:
            message = f"本次无新黄金预测：{exc}。不要转发旧价格、旧图或旧置信度。"
            print(message, file=sys.stderr)
            with log.open("a") as fh:
                fh.write("\n" + message + "\n")
            alert = run / "alert.md"
            alert.write_text("# 黄金数据告警\n\n" + message + "\n")
            paths["report_md"] = alert
            manifest.update(status="no_forecast", reason=str(exc))
        manifest["generated_at"] = timestamp()
        manifest["files"] = {k: str(p.relative_to(folder)) for k, p in paths.items()}
        manifest["sha256"] = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
        for key, alias in ALIASES.items():
            if key in paths:
                atomic(folder / alias, paths[key].read_bytes())
            else:
                (folder / alias).unlink(missing_ok=True)
        atomic(run / "manifest.json", encoded(manifest))
        atomic(folder / "manifest.json", encoded(manifest))
        print(f"{manifest['status']} {run}")
        return 0 if manifest["status"] == "ok" else 2


def acknowledge(folder, run_id, message_id):
    import re
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}", run_id) or not message_id.strip():
        raise ValueError("invalid run ID or message ID")
    run = folder / "runs" / run_id
    raw = (run / "manifest.json").read_bytes()
    if json.loads(raw)["run_id"] != run_id:
        raise ValueError("run mismatch")
    receipt = run / "delivery.json"
    data = dict(run_id=run_id, feishu_message_id=message_id, acknowledged_at=timestamp(),
                manifest_sha256=hashlib.sha256(raw).hexdigest())
    # Atomic create, never replace an existing delivery receipt.
    with tempfile.NamedTemporaryFile(dir=run) as tmp:
        tmp.write(encoded(data))
        tmp.flush()
        try:
            os.link(tmp.name, receipt)
        except FileExistsError:
            if json.loads(receipt.read_bytes())["feishu_message_id"] != message_id:
                raise ValueError("different receipt already recorded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("target", nargs="?")
    parser.add_argument("--ack", nargs=2, metavar=("RUN_ID", "FEISHU_MESSAGE_ID"))
    args = parser.parse_args()
    if args.ack:
        acknowledge(args.output, *args.ack)
    else:
        sys.exit(issue(args.output, args.target or None, ["--skip-backtest"]))
