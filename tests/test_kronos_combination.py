import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ml-service'))
from models.kronos_combination import mature_history, predict_combination, calibrated_radius


def test_unmatured_labels_cannot_influence_combination():
    dates=pd.bdate_range('2025-01-01',periods=80)
    data=pd.DataFrame({'origin_date':dates,'target_date':dates+pd.Timedelta(days=7),'horizon':5,
        'actual_return':np.sin(np.arange(80))*.01,'gbm_return':np.cos(np.arange(80))*.01,
        'vol20':.01,'kronos_return':.005,'path_std':.01,'path_up_fraction':.5,'disagreement':.002})
    current=data.iloc[60].to_dict()
    before=predict_combination(data,current,True)
    data.loc[data.target_date>current['origin_date'],'actual_return']=999.
    assert predict_combination(data,current,True)==before
    eligible=mature_history(data,current['origin_date'],5)
    assert (eligible.target_date<=current['origin_date']).all()
    assert (eligible.origin_date<current['origin_date']).all()


def test_interval_calibration_excludes_unresolved_forecasts():
    dates=pd.bdate_range('2025-01-01',periods=60)
    data=pd.DataFrame({'origin_date':dates,'target_date':dates+pd.Timedelta(days=7),'horizon':5,
                       'actual_return':.01,'pred_return':0.})
    radius,n=calibrated_radius(data,dates[50],5)
    data.loc[data.target_date>dates[50],'actual_return']=999.
    assert calibrated_radius(data,dates[50],5)==(radius,n)
    assert radius==.01 and n>=30
