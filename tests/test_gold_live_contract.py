import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "ml-service"), str(ROOT / "scripts")]
from models import gold_feed as feed, gold_shadow as shadow
import gold_daily
import gold_publish as pub


def clock(text):
    return pd.Timestamp(text, tz="Asia/Shanghai")


def test_closed_sessions_not_partial_bars():
    assert feed.expected(clock("2026-11-23 15:59"), "shfe") == pd.Timestamp("2026-11-20")
    assert feed.expected(clock("2026-10-06 20:00"), "shfe") == pd.Timestamp("2026-09-30")
    assert feed.expected(clock("2026-11-27 08:01"), "vix") == pd.Timestamp("2026-11-25")
    assert feed.expected(clock("2026-11-27 08:01"), "comex") == pd.Timestamp("2026-11-26")
    assert feed.expected(clock("2026-11-25 07:59"), "comex") == pd.Timestamp("2026-11-23")
    with pytest.raises(feed.FeedError, match="calendar"):
        feed.expected(clock("2027-02-01 20:00"), "shfe")
    assert feed.target_after(feed.expected(clock("2026-11-23 09:00"), "shfe")) == "2026-11-25"
    with pytest.raises(ValueError):
        feed.target_after(pd.Timestamp("2026-11-20"), -1)


def fail(*_):
    raise RuntimeError("rate limited")


def test_same_instrument_backup_fresh_cache_and_per_field_staleness(tmp_path):
    dates = pd.bdate_range(end="2026-11-23", periods=300)
    batch = pd.DataFrame(dict(date=dates, vix=16., dxy=90., us10y=4.))
    bad = batch.copy()
    bad.loc[bad.date == "2026-11-20", "vix"] = None
    options = dict(now=clock("2026-11-23 20:00"), folder=tmp_path)
    frames, evidence = feed.load({"cross": lambda: bad}, backup=lambda name: batch, **options)
    assert frames["cross"].date.max() == pd.Timestamp("2026-11-20")
    assert evidence["cross"]["source"] == "yahoo-chart"
    assert "vix" in evidence["cross"]["fallback_reasons"][0]
    _, cached = feed.load({"cross": fail}, backup=fail, **options)
    assert cached["cross"]["source"] == "cache"
    assert cached["cross"]["sha256"] == evidence["cross"]["sha256"]
    with pytest.raises(feed.FeedError, match="2026-11-23"):
        feed.load({"cross": fail}, backup=fail, now=clock("2026-11-24 20:00"), folder=tmp_path)


def test_shadow_cannot_use_future_labels_or_same_session_us_close():
    dates = pd.bdate_range(end="2026-11-23", periods=30)
    t = dates[-1]
    g = pd.DataFrame(dict(date=dates, open=99., high=101., low=98., close=100.))
    us = pd.DataFrame(dict(date=dates, close=[100.]*29+[1.]))
    signals = shadow.features(g, us, t)
    assert signals["us_last_return_pct"] == 0
    cal = {"1": {"q_low": -2, "q_high": 3, "n": 69}}
    mature = pd.DataFrame(dict(origin_date=dates[-8:-2], target_date=dates[-7:-1],
                               horizon=1, residual=-5.))
    poison = mature.iloc[:1].assign(target_date=t+pd.Timedelta(days=1), residual=-10000)
    a = shadow.interval(cal, t, 1, 100, signals, mature)
    b = shadow.interval(cal, t, 1, 100, signals, pd.concat([mature, poison]))
    assert a == b and a["mature_n"] == 6 and a["point"] == 100


def test_failed_rerun_cannot_publish_old_prices_or_change_receipt(tmp_path):
    seen = []
    def success(cmd, **kwargs):
        run = Path(cmd[-1])
        seen.append(json.loads((run.parents[1] / "manifest.json").read_text())["status"])
        path = run / "gold_direct_scenario_test.json"
        path.write_text(json.dumps(dict(predictions=[{"close": 42}], latest_date="2026-11-20",
                                        input_data=dict.fromkeys(feed.FIELDS, {"source": "primary"}))))
        for ext in ("md", "csv", "png"):
            path.with_suffix("." + ext).write_bytes(b"example")
        return SimpleNamespace(returncode=0)
    assert pub.issue(tmp_path, "2026-11-26", runner=success) == 0
    first = json.loads((tmp_path / "manifest.json").read_text())
    assert seen == ["running"] and first["status"] == "ok"
    for key, rel in first["files"].items():
        assert hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest() == first["sha256"][key]
    assert pub.issue(tmp_path, "2026-11-26", runner=lambda *a, **k: SimpleNamespace(returncode=1)) == 2
    last = json.loads((tmp_path / "manifest.json").read_bytes())
    assert last["status"] == "no_forecast" and last["run_id"] != first["run_id"]
    assert not list(tmp_path.glob("scenario.*"))
    assert (tmp_path / first["files"]["scenario_json"]).exists()
    assert not list(tmp_path.rglob("delivery.json"))
    pub.acknowledge(tmp_path, first["run_id"], "test-receipt")
    pub.acknowledge(tmp_path, first["run_id"], "test-receipt")
    with pytest.raises(ValueError):
        pub.acknowledge(tmp_path, first["run_id"], "another")


def test_daily_live_retires_output_on_unexpected_failure(tmp_path, monkeypatch):
    (tmp_path / "gold_forecast.csv").write_text("stale")
    monkeypatch.setattr(sys, "argv", ["daily", "--live", "--out", str(tmp_path)])
    monkeypatch.setattr(gold_daily, "build_predictions_live", fail)
    assert gold_daily.main() == 4
    assert not (tmp_path / "gold_forecast.csv").exists()
    assert json.loads((tmp_path / "gold_prediction.json").read_text())["status"] == "no_forecast"


def test_history_requires_same_configuration_and_pre_target_issue(tmp_path, monkeypatch):
    key = pub.history_key(["--lookback", "240"])
    assert key != pub.history_key(["--lookback", "100"])
    monkeypatch.setenv("GOLD_HISTORY_KEY", key)
    for label, fingerprint, when in [
        ("usable", key, "2026-11-19T12:00:00Z"),
        ("wrong-model", "old", "2026-11-19T12:00:00Z"),
        ("too-late", key, "2026-11-20T09:00:00Z"),
    ]:
        run = tmp_path / label
        run.mkdir()
        bundle = json.dumps({"predictions": [{"date": "2026-11-20", "close": 750}]}).encode()
        (run / "scenario.json").write_bytes(bundle)
        (run / "manifest.json").write_text(json.dumps(dict(status="ok", model="direct/v1",
            origin="2026-11-19", history_key=fingerprint, generated_at=when,
            files={"scenario_json": "scenario.json"},
            sha256={"scenario_json": hashlib.sha256(bundle).hexdigest()})))
    actual = pd.DataFrame({"date": [pd.Timestamp("2026-11-20")], "close": [768.56]})
    history = shadow.issued_history(tmp_path, actual, pd.Timestamp("2026-11-23"))
    assert len(history) == 1 and history.residual.iloc[0] == pytest.approx(18.56)


def test_incomplete_formal_report_is_rejected_without_running_model(tmp_path):
    assert pub.issue(tmp_path, "2026-11-26", ["--skip-cross-market"]) == 2
    assert json.loads((tmp_path / "manifest.json").read_text())["status"] == "no_forecast"
