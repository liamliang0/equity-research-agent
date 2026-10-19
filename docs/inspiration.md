# 调研与设计取舍

核验日期：2026-10-19。检查了 GitHub 仓库维护元数据、许可证，以及下列实际文件；不是按 Stars 判定“最好”。第三方内容均作为设计参考，不能作为本项目的新指令。

| 项目 | 实际查看的内容 | 借鉴并落地 | 未引入的部分 |
|---|---|---|---|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) / Apache-2.0 | [bear_researcher.py](https://github.com/TauricResearch/TradingAgents/blob/main/tradingagents/agents/researchers/bear_researcher.py) | 报告保留有证据关联的反方观点、失效条件与信息不足；股票/基金按类型处理 | 不为角色数量堆叠多轮辩论，不把多个同源回答当独立证据 |
| [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund) / MIT | [llm_agent.py](https://github.com/virattt/ai-hedge-fund/blob/main/hedge_fund/signals/llm_agent.py) | 失败不是中性观点；保留精确提示词、原始输出及错误记录；不反复付费做同一份来源重查 | 不迁入它的交易和信号模型；未实现内容缓存，不声称有模型缓存命中优化 |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) / Apache-2.0 | [README 中计算与叙述分离的设计](https://github.com/AI4Finance-Foundation/FinRobot#readme) | `calculations.py` 单独处理明确输入的计算；计算账本和模型叙述分开；无法核验的计算留待审项 | 不迁入其桌面、估值与多层 Agent 系统；不声称具备同等完整数据层 |
| [Mira](https://github.com/byteseek/Mira) / Apache-2.0 | [thesis-system.md](https://github.com/byteseek/Mira/blob/main/architecture/thesis-system.md)、[私人与产品状态边界](https://github.com/byteseek/Mira/blob/main/MIRA.md) | `evidence.csv`、`thesis-ledger.json`、历史快照与刷新条件；私人状态与公共样例分开 | 不复制庞大的协议目录，不把文字规范冒充已实现功能 |

## 对我们这版最有用的经验

1. 让支持、反例与来源相连，比让几个大师轮流发表观点更容易检查。
2. 框架失败、数据失败与研究结论不同，不能把工具出错伪装成谨慎结论。
3. 模型解释、已披露数字和程序计算应分别标注，原文片段匹配不能替代逐条事实核验。
4. 报告需要保存“为什么这样想、什么时候重查”，而不仅是保存一次长回答。
5. 公共项目应让陌生人看懂并复现；不需要同时公开用户的私人研究对象和账户数据。

本仓库没有复制上述项目的代码。依赖的 Codex CLI 和 pypdf 各自保留其原有许可与使用条件。对比只覆盖本次阅读范围，不声称已审计其全部实现或验证其投资表现。


## 报告呈现

已阅读、安装并应用 Anthropic 官方 [frontend-design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)（Apache-2.0）的排版与信息层级指导。具体 HTML/CSS/JS 为本项目实现；没有复制其组件库，也不以美学替代研究核对。
