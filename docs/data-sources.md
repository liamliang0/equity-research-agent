# 数据接口与实际运行

这是只读公共数据层，不接交易，不把连接器名称当作数据已验证的证明。

| 适配器 | 实际读取 | 关键处理 |
|---|---|---|
| SEC EDGAR Company Facts | 每家发行人的标准XBRL字段 | CIK先经submissions的精确ticker校验；保留tag、币种、单位、起止日、申报日、accession |
| US Treasury XML | 最近可用的3个月、2年、10年、30年国债收益率 | 只取截止日或之前观测；单位是百分比；不把国债收益率等同WACC |
| Yahoo Finance chart | 股票/ETF的最近常规交易时段价格及市场时间 | 非官方、best effort接口；不承诺实时订阅；周末旧时点保留原日期，失败不填0 |

官方说明：[SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)、[Treasury XML](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rate-xml-files)。行情接口使用原始JSON中的provider与时点，不能称为官方交易所行情。

## 使用

```bash
# 单独取数，不调用AI、不要求券商登录
python market_data.py --watchlist watchlist.example.json --output output/data
# 新研究流程会先读取接口，再把结构化观测加入第二轮AI证据包
python showcase.py
# 已有研究/审阅：只刷新数据和缺口状态，不冒充重新做过AI分析
python showcase.py --research-file examples/research-packet.json --output output/showcase --refresh-data-only
```

SEC股票总映射可能403。可以在名单对象中提供`sec_cik`，程序仍会读取官方submissions核对ticker；身份不匹配则拒绝财报关联，不猜ADR对应关系。公开默认配置中AAPL用于演示，私人名单不发布。

每次保存`data/data-snapshot.json`与`data/raw/<sha256>.raw`。快照包含实际端点、HTTP状态、获取时间、响应指纹、失败原因与覆盖率；原始文件可用于复盘。没有悄悄用过期缓存代替本次成功响应。

## 如何进入分析

结构化数据不是网页装饰：`market_data.evidence`将其生成`api-quote-*`、`api-sec-*`和`api-treasury`证据；第二轮模型可以引用这些ID，程序校验跨公司引用。财报原始观察和模型解释分开，不把“接口有响应”标成“财务解释已审计”。

`--refresh-data-only`不调用模型，只更新明确可观察的报价、利率和缺口状态。原AI假设、观点和审阅时间仍保留；页面明确标注它们未被重新分析。

## 仍需判断的内容

- 单季、年内累计和全年数据分别显示；没有将九个月现金流冒充单季，也没有自动年化。
- 标准tag可能缺失、自定义tag未覆盖或历史字段较旧；显式展示缺口和旧期间，不用0代替。
- ETF不套普通公司财报；ADR/外币财报不自动换算成美元每股价值。
- 行情、财报和利率是观测；未来增长、利润率、再投资和风险溢价是需说明依据的假设。接口接通不等于合理价已算出。
- IBKR App连接器和本地Python是不同执行环境；当前不声称本地脚本能自动调用用户的IBKR账号。App行情探测失败不能冒充已接上实时券商行情。

请求采用不含用户邮箱的通用User-Agent，两工作线程、最多重试一次，不申请付费API，不发送私有持仓数量、成本或盈亏。
