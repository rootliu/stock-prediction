# 黄金预测 Agent 调用手册

本文档是 `stock-prediction` 中黄金预测流程的 agent 调用契约，目标是让其它 agent 可以直接发起预测、读取结果、在必要时回退模型。

## 当前变更

当前黄金流程已经切换到下面这组默认约定：

- 默认预测粒度：`4h`
- 默认预测策略：`ensemble`
- 推荐数据源：`SHFE_AU_MAIN`
- 可回退策略：`boosting`、`linear`

`ensemble` 的角色不是替代回退路径，而是在默认情况下做一个更稳的组合预测：

- 线性模型提供更保守的基线
- boosting 提供更强的短期幅度拟合
- 外部趋势只做约束和校正，不直接当第三条平均线

所以其它 agent 默认应调用 `ensemble`，只有在对照实验或回退排障时才显式切到 `boosting` 或 `linear`。

## 推荐调用方式

对无界面 agent，优先使用 wrapper 脚本：

```bash
/Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

这会直接生成完整报告包，默认值如下：

- `OPENCLAW_LOOKBACK=120`
- `OPENCLAW_PREDICT_MODEL=ensemble`
- `OPENCLAW_SESSION_PERIOD=4h`
- `OPENCLAW_REPORT_SOURCE=SHFE_AU_MAIN`

如果 agent 只是消费结果，不需要自行拼接多张图表和 CSV，优先走这条路径。

## 回退控制

需要回退时，用环境变量显式指定模型：

```bash
OPENCLAW_PREDICT_MODEL=ensemble /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=boosting /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
OPENCLAW_PREDICT_MODEL=linear /Users/rootliu/code/stock-prediction/scripts/run_openclaw_report.sh /tmp/agent-gold-report
```

选择建议：

- `ensemble`：默认生产路径，平衡激进度和稳定性
- `boosting`：更激进，适合做对照
- `linear`：最保守，适合做基线或排障

## 直接调用 CLI

如果 agent 需要自己控制参数，可以直接调用 `run.py`：

```bash
cd /Users/rootliu/code/stock-prediction
python run.py \
  --bot-output-dir /tmp/agent-gold-report \
  --report-source SHFE_AU_MAIN \
  --horizon 5 \
  --lookback 120 \
  --predict-model ensemble \
  --session-period 4h
```

注意：

- 只要传了 `--bot-output-dir` 或 `--openclaw-output-dir`，程序就会进入无界面报告模式
- 不传输出目录时，程序默认进入图形界面模式

## 直接调用 HTTP API

如果 agent 只需要结构化预测值，不需要整包报告，可以直接打接口。

启动 ML 服务：

```bash
cd /Users/rootliu/code/stock-prediction/ml-service
python main.py
```

获取默认 `4h` 预测：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{
    "horizon": 5,
    "lookback": 120,
    "model_type": "ensemble"
  }'
```

回退示例：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{"horizon": 5, "lookback": 120, "model_type": "boosting"}'

curl -sS -X POST http://127.0.0.1:8000/api/v1/gold/predict/SHFE_AU_MAIN \
  -H 'Content-Type: application/json' \
  -d '{"horizon": 5, "lookback": 120, "model_type": "linear"}'
```

读取辅助数据：

```bash
curl -sS 'http://127.0.0.1:8000/api/v1/gold/quote/SHFE_AU_MAIN'
curl -sS 'http://127.0.0.1:8000/api/v1/gold/session/SHFE_AU_MAIN?period=4h&days=5'
curl -sS 'http://127.0.0.1:8000/api/v1/gold/kline/SHFE_AU_MAIN?period=4h&session=ALL'
```

## 输出契约

如果使用 bot/report 模式，下游 agent 应遵守以下读取方式：

1. 先等待 `manifest.json`
2. 再读取 `report.md` 获取人类可读摘要
3. 再读取结构化文件和图像

核心文件：

- `manifest.json`
- `report.md`
- `gold_quote.json`
- `gold_prediction.json`
- `gold_history.csv`
- `gold_forecast.csv`
- `gold_compare.csv`
- `gold_session.csv`
- `external_gold_survey.csv`
- `gold_curve_comparison.csv`
- `gold_external_main_curve.csv`

图像与表格：

- `gold_prediction.png`
- `gold_compare.png`
- `gold_session.png`
- `gold_curve_comparison.png`
- `gold_summary_table.png`
- `gold_forecast_table.png`
- `gold_external_survey_table.png`
- `gold_curve_comparison_table.png`

`manifest.json` 是完成标记。没有它时，不要把目录当成一轮完整输出。

## 返回字段说明

调用 `/api/v1/gold/predict/...` 时，agent 至少应关注这些字段：

- `period`：实际建模粒度。国内黄金主流程默认应为 `4h`
- `model.name`：实际执行的模型名称
- `predictions[]`：逐步预测点
- `metrics.mape`：内部回测误差指标

目前可能出现的 `model.name`：

- `ensemble_linear_boosting_external_v1`
- `gradient_boosting_direction_head`
- `linear_regression_direction_head`

如果是 `ensemble`，响应里的元数据会保留回退相关信息，方便 agent 做日志记录或诊断。

## 对其它 Agent 的建议

推荐默认策略：

1. 优先调用 wrapper 脚本生成整包报告
2. 默认使用 `ensemble`
3. 只在比对或排障时切到 `boosting` / `linear`
4. 默认读取 `4h` 结果，不要把 `15min/30min` 当成生产默认入口

如果下游 agent 只需要一份简报，最小读取集就足够：

- `report.md`
- `gold_prediction.json`
- `gold_forecast.csv`
- `gold_forecast_table.png`
