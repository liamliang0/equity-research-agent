# 项目如何进入简历

项目名：**Equity Research Agent｜AI 辅助证券研究工作流**

适用证据：公开报告、证据表、判断账本、失败与修复记录；不是投资业绩证明，也不把本人包装成开发工程师或成熟证券分析师。

## 中文项目描述

- 将个人研究框架拆为产业、成长、预期、宏观、质量与风险任务，配置 Codex 完成联网研究与第二轮审阅，保留原判断、批评、修订和下一步验证任务。
- 接入行情、SEC XBRL财报与美国财政部利率，定义时点、期间、币种及发行人身份校验；使用 Python 执行情景估值与敏感性计算，公开展示证据追溯及失败处理。
- 负责问题定义、流程配置、验证标准和结果审阅；使用 Codex 辅助实现，公开可复现样例及已知限制。

## English

- Translated a personal research framework into six analytical tasks and configured a two-pass Codex workflow: live research followed by a separate evidence-grounded critique with explicit revisions and follow-up experiments.
- Defined citation and source checks and used Python for scenario valuation, reverse-growth solving and sensitivity analysis; published an auditable case with reconciled TTM cash flow, explicit assumptions and interactive sensitivity analysis.
- Owned problem framing, workflow configuration, validation criteria and output review; used Codex for implementation and published reproducible examples with limitations.

## 面试能解释的内容

1. 为什么做：一次问答难以保留判断依据和下次检查条件，因此把研究变成可重复运行流程。
2. 哪些是你做的：研究问题、证券分流、输出结构、来源规则、测试验收和基于真实失败的迭代决策。代码实现由 Codex 辅助。
3. Agent 做什么：在目标、来源范围和结构要求内选择检索并分析；程序再检查引用和原文。
4. 哪些是确定性代码：日期与引用检查、原文片段匹配、明确输入的 Decimal 计算、文件指纹；不是让模型自己宣称“已验证”。
5. 真正遇到的失败：官方财报 PDF 超过旧上限；曾显示待复核，修复解析和大小限制后仅重做来源检查，没有再付费生成同一份分析。
6. 当前边界：原文匹配不是完整事实核查；ETF集中度、ADR换算和跨币种比较需要相应数据；模型依然可能出错。
7. 为什么增加第二轮：明确审阅第一轮的具体结论，并留下实际修订；它共享证据，不叫独立专家共识。六项视角是任务，不是六位大师人格。
8. 估值展示的边界：公开 AVGO 案例使用实际报价与披露，期间衔接后运行现金流代理模型；假设和高终值占比显式展示，不将条件结果当精确目标价。旧虚构输入仅保留为工程测试。

项目链接：https://github.com/liamliang0/equity-research-agent
