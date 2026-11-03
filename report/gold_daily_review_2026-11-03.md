# 黄金每日任务同步与可靠性修复

日期：2026-11-03（Asia/Shanghai）

## 同步范围

从 GitHub main 快进接收 8a34705、b1f43a1、830b085，包含版本注册、离线排行榜、每日服务任务、缓存及账本回填。
本地已有的新闻快照没有加入提交，也没有覆盖。

## 修复

| 问题 | 修复 | 验证 |
|---|---|---|
| 历史起点对应的远期实际价格可提前进入回退判断 | 同时约束预测起点和目标到期日 | 改变未来实际价格不改变当前 skill |
| 无穷值、非法日期、重复行可能生成误导报告 | 输入统一校验，数据错误返回 2 | 参数化异常测试 |
| 回退后读者可能将候选 skill 误认为基线成绩 | JSON 和 Markdown 记录评估版本、截止点和样本数 | 离线主流程测试 |
| 价格区间容易误读为方向信心 | 明确 direction_probability_status=not_estimated | 输出字段断言 |

## 验证命令

```sh
MPLCONFIGDIR=/tmp/mpl-stock .venv/bin/python -m pytest \
  tests/test_versions.py tests/test_gold_integrity.py tests/test_kronos_combination.py \
  scripts/test_direction_confidence.py scripts/test_gold_continuation.py \
  scripts/test_confidence_evaluation.py -q
```

42 项通过，包括离线任务输出集成测试。环境存在 matplotlib/pyparsing 弃用及 LibreSSL 警告。

## 结论与边界

这次是流程正确性改进，不是新行情准确率评估；未抓取实时行情、未重训或更改模型参数。
远端保存的排行榜显示 v7 平均 skill 为 -0.0131，directional edge=False；这是历史冻结评测，不是今天的成绩。
现有生产入口、cron 和 OpenClaw 配置未改动。原生产入口仍可使用，新增改动可通过独立 Git 提交回退。

后续优先事项：缓存新鲜度阈值与交易日校验、校准文件训练截止日期校验、按期限和非重叠样本审计 skill。
当前校准文件是全样本残差分位数，缺少训练截止元数据，因此不应将每日任务的历史区间当作严格样本外回测结果。
滚动窗口中的多期限样本仍相关；缺少足够独立证据时，不应发布高置信度涨跌判断。
