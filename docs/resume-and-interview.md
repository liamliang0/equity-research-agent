# 项目如何进入简历

项目名：**Equity Research Agent｜AI 辅助证券研究工作流**

适用证据：公开报告、证据表、判断账本、失败与修复记录；不是投资业绩证明，也不把本人包装成开发工程师或成熟证券分析师。

## 中文项目描述

- 从个人研究需求出发，配置 Codex 与 Python 工作流，按股票、ADR、ETF 拆分研究任务，自动检索官方资料并整理支持证据、反例和待验证事项。
- 定义来源、日期、引用及覆盖检查，针对 PDF 读取和官网抓取失败迭代流程；输出可追溯的报告、证据表和判断账本，支持后续复核与更新。
- 负责问题定义、流程配置、验证标准和结果审阅；使用 Codex 辅助实现，公开可复现样例及已知限制。

## English

- Configured a Codex-assisted research workflow that routes equities, ADRs and ETFs to instrument-specific questions and organizes official disclosures into evidence, counterarguments and follow-up checks.
- Defined source, date, citation and coverage checks; improved PDF handling and failure reporting, producing traceable research memos and evidence/thesis ledgers.
- Owned problem framing, workflow configuration, validation criteria and output review; used Codex for implementation and published reproducible examples with limitations.

## 面试能解释的内容

1. 为什么做：一次问答难以保留判断依据和下次检查条件，因此把研究变成可重复运行流程。
2. 哪些是你做的：研究问题、证券分流、输出结构、来源规则、测试验收和基于真实失败的迭代决策。代码实现由 Codex 辅助。
3. Agent 做什么：在目标、来源范围和结构要求内选择检索并分析；程序再检查引用和原文。
4. 哪些是确定性代码：日期与引用检查、原文片段匹配、明确输入的 Decimal 计算、文件指纹；不是让模型自己宣称“已验证”。
5. 真正遇到的失败：官方财报 PDF 超过旧上限；曾显示待复核，修复解析和大小限制后仅重做来源检查，没有再付费生成同一份分析。
6. 当前边界：原文匹配不是完整事实核查；ETF集中度、ADR换算和跨币种比较需要相应数据；模型依然可能出错。
7. 为什么不做多个大师：支持与反例要有共同证据基础；重复角色不能当成独立研究，也不值得只为展示而增加调用。

项目链接：https://github.com/liamliang0/equity-research-agent
