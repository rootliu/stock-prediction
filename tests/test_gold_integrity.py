"""Guard actual information boundaries, not numerical implementation snapshots."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml-service"))
from models.market_availability import available_observations, availability_audit, daily_cutoff
from models import multi_day_direct_predictor as m


def test_date_only_external_bar_is_not_available_same_afternoon():
    frame = pd.DataFrame({'date': pd.to_datetime(['2026-03-06','2026-03-09']), 'close':[100,999]})
    got = available_observations(frame, daily_cutoff(pd.Timestamp('2026-03-09')))
    assert got.close.tolist() == [100]
    audit=availability_audit(frame,daily_cutoff(pd.Timestamp('2026-03-09')))
    assert audit['last_source_date']=='2026-03-06'
    assert audit['last_available_at']=='2026-03-07T08:00:00+08:00'


def test_late_revision_and_timezones_respect_availability():
    frame = pd.DataFrame({'date': pd.to_datetime(['2026-03-06']*2), 'close':[100,999],
                          'available_at':['2026-03-06T16:00:00-05:00','2026-03-09T09:00:00Z']})
    got = available_observations(frame, daily_cutoff(pd.Timestamp('2026-03-09')))
    assert got.close.tolist() == [100]
    later = available_observations(frame, pd.Timestamp('2026-03-09T18:00:00+08:00'))
    assert later.close.tolist() == [999]


def test_ambiguous_availability_is_rejected():
    frame=pd.DataFrame({'date':[pd.Timestamp('2026-01-01')],'available_at':['2026-01-02 08:00']})
    with pytest.raises(ValueError, match='timezone'):
        available_observations(frame,daily_cutoff(pd.Timestamp('2026-01-02')))
    with pytest.raises(ValueError, match='16:00'):
        daily_cutoff(pd.Timestamp('2026-01-02'),pd.Timestamp('2026-01-02T12:00:00+08:00'))


@pytest.fixture
def market():
    date=pd.bdate_range('2025-01-01',periods=125)
    close=600 + np.arange(125)*.1 + np.sin(np.arange(125))*5
    daily=pd.DataFrame(dict(date=date,open=close-.2,high=close+1,low=close-1,close=close,volume=1000.))
    empty=pd.DataFrame({'date':pd.Series(dtype='datetime64[ns]')})
    return daily,empty


def test_validation_labels_are_purged_and_final_fit_uses_mature_labels(market):
    daily,empty=market
    model=m._train_horizon_model(daily,empty,empty,empty,5,80)
    metrics=model['metrics']
    assert metrics['purged_size']==4
    assert metrics['last_validation_train_label'] <= metrics['first_validation_origin']
    assert metrics['refit_size']==80 > metrics['train_size']
    assert metrics['last_refit_label']==str(daily.iloc[-1].date.date())


def test_future_external_values_do_not_change_historical_features(market):
    daily,empty=market
    date=daily.iloc[-1].date
    external=pd.DataFrame({'date':pd.to_datetime([date-pd.Timedelta(days=1),date]),'close':[2000.,1.]})
    kw=dict(daily_history=daily.tail(21),current_close=float(daily.iloc[-1].close),current_date=date,
            usdcny_daily=empty,cross_market=empty,horizon_days=1)
    first=m._build_direct_feature_row(comex_daily=external,**kw)
    external.loc[1,'close']=999999.
    assert first==m._build_direct_feature_row(comex_daily=external,**kw)


def test_backtest_failure_is_not_silently_dropped(market,monkeypatch):
    daily,empty=market
    def fail(**kwargs): raise ValueError('intentional test failure')
    monkeypatch.setattr(m,'run_direct_multi_day_prediction',fail)
    with pytest.raises(RuntimeError,match='origin'):
        m.rolling_backtest_direct(daily,empty,empty,empty,lookback=80,max_horizon=1)


def test_missing_horizon_cannot_be_relabelled(market,monkeypatch):
    daily,empty=market
    monkeypatch.setattr(m,'run_direct_multi_day_prediction',lambda **kwargs: [])
    with pytest.raises(RuntimeError,match='Missing/duplicate'):
        m.rolling_backtest_direct(daily,empty,empty,empty,lookback=80,max_horizon=3)
