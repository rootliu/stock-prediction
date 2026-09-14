# 黄金改进任务状态与恢复入口

## 当前检查点（2026-09-14，优先于下方历史待办）

用户已决定暂停进一步模型修改与调参，要求记录并同步GitHub。当前冻结 GitHub `8418fad` 加本机已有修复的合并版本。三组新回测共783条全部完成，本机版在60个共同起点的四个周期均未胜过价格不变基线。详见 [检查点与恢复决定](GOLD_CHECKPOINT_2026-09-14.md) 和 [9/13回测报告](../report/review_20260913/README.md)。下方研究待办仅作历史参考，不据此自动启动新优化；邮件部署仍属独立工作。

用户已授权实施回测审查中的改进，并要求断开终端后仍可恢复工作。以下后台程序只运行固定实验，不自动提交、推送或选择生产模型。

## 最近检查（2026-09-07）

- 10 项针对性测试通过（含邮件内容测试）；两起点串行、并行与重复启动续跑验证通过。
- 上次后台启动被沙箱阻止，权限申请中断，故当时完整研究尚未运行。
- 2026-09-07 完整研究完成，280/280 起点，失败工作进程为零，审计通过。200 个评估起点中所有候选模型均落后价格不变基线。详见 `report/improvement_20260907/README.md`。
- 用户新增每天北京时间07:00邮件推送需求。脚本和部署说明已准备，缺少发信服务，尚未安装调度或实发；详见 `docs/GOLD_DAILY_EMAIL.md`。
- 下一步：接通邮件配置并验证投递；此前拟增加的模型准入/回退机制尚未实施。
- 输出：`analysis_outputs/gold_research_v1/`。完成与否以最新 `status.json`、覆盖率及 `RESULTS.md` 为准。
- 所有修改仍在本地工作区，未提交/推送。

## 当前实现

- daily GBM：按 available_at 过滤外部数据；缺少时间戳时明确使用次日上海 08:00 的保守假设。
- 按标签成熟日期 purge 验证集；保留验证指标，最终用全部已成熟样本重训。
- 全局偏差校正改用验证残差；不再使用分支训练内残差。confidence 明确标记为启发分数。
- 回测异常/缺失 horizon 不再静默跳过。
- `run_gold_research.py`：200 个评估起点 + 80 个较早起点；固定快照、模型版本、路径采样参数；逐日起点原子写入和排他锁。
- `kronos_combination.py`：只用已经成熟的历史预测训练 Ridge 组合及概率/区间校准；组合仍属研究模块。
- `summarize_gold_research.py`：共同样本、逐月对照、区间覆盖率、Brier score、时间块 bootstrap。

## 执行与恢复

```bash
cd /root/code/codex/stock-prediction
bash scripts/gold_research_job.sh start
bash scripts/gold_research_job.sh status
tail -n 30 analysis_outputs/gold_research_v1/worker.log
```

重复 start 会检查现有 tmux 会话；进程退出后再次 start 会跳过已经完成的起点。正常运行不依赖交互终端，但依赖主机、文件系统和进程继续存在；主机重启后需重新执行 start。

Python 默认 `/tmp/gold-backtest-venv/bin/python`，官方 Kronos 代码 `/tmp/gold-kronos-official`，权重 `/tmp/gold-kronos-weights`。这些临时依赖被清理时需要重新准备，可参考 `report/review_20260906/README.md` 和固定版本下载脚本。

工作进程会校验代码、数据、依赖及权重。代码改变后不能混入旧实验；请用新的 `GOLD_RESEARCH_OUTPUT` 目录启动。结果中 `coverage.csv`、`status.json` 和每个 origin JSON 用于核对成功/失败，不以日志里的最后一句作为完成依据。

Codex 会话恢复与后台作业是两回事。CLI 支持恢复会话（见[官方文档](https://learn.chatgpt.com/docs/codex/cli)）；后台实验本身不能在助手会话停止后自动进行新的代码分析和修改。恢复助手后先读取本文件和最新 status/RESULTS，再继续下面的工作。

## 后续检查清单

1. 跑完 tests；用小型实验验证保存、恢复及月度汇总。
2. 启动并完成 200 起点后台研究，检查所有阶段覆盖率和数据/代码哈希。
3. 检查 fixed_gbm 相对 legacy_aligned 的变化，以及 meta_kronos 相对 meta_gbm 的增量；不要只与旧 GBM 比较后就宣称 Kronos 有贡献。
4. 写结果报告及限制；若没有稳定增益，不启用组合模型作为生产默认。
5. 微调需在输入口径与零样本实验明确后再评估，不在本轮测试段调参。

生产数据采集尚未提供逐条真实发布时间，当前回退时间仍是标注的假设；研究属于历史回放，部分旧 guard 开发日期与历史窗口重合，不能冒充封存的前瞻测试。
