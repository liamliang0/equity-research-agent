"""Research-first, offline HTML presentation. No telemetry or external frontend dependencies."""
import html
import json
from pathlib import Path
import case_research
import data_view
import utilities as u

e=lambda value:html.escape(str(value))
bn=lambda value:f'{value/1e8:,.2f}'
pct=lambda value:f'{value*100:.1f}%'


def render(report,review,telemetry,output,case,private=False):
    output=Path(output); snapshot=report['data_snapshot']; symbol=case['symbol']; profile=case['profile']
    source={s['id']:s for s in profile['sources']}
    price=case['quote']['price']; base=case['scenarios']['base']; bridge=case['bridge']; implied=case['implied_growth']
    view_text='TTM基准情景低于当前报价；需要更快的现金流增长或更低的折现率才能支持价格。' if base['value_per_share']<price else 'TTM基准情景能够覆盖当前报价；结论仍取决于增长持续性与折现率假设。'
    evidence=''.join(f'<li><h3>{e(x["title"])}</h3><p>{e(x["fact"])}</p><p class="interpretation">判断：{e(x["interpretation"])}</p><a href="{e(source[x["source"]]["url"])}" target="_blank" rel="noopener noreferrer">查看原始披露</a></li>' for x in profile['evidence'])
    views=''.join(f'<div class="view-row"><h3>{e(x["name"])}</h3><div><p>{e(x["view"])}</p><p class="muted">需要挑战：{e(x["challenge"])}</p></div></div>' for x in profile['different_views'])
    watch=''.join(f'<tr><th>{e(x["signal"])}</th><td>{e(x["test"])}</td><td>{e(x["invalidates"])}</td></tr>' for x in profile['watch'])
    key_rows=[('TTM收入',case['ttm']['revenue']['value']),('经营现金流',bridge['cfo']),('减：固定资产现金支出',-bridge['capex']),('减：股权薪酬经济成本',-bridge['sbc']),('加：税后现金利息代理',bridge['after_tax_cash_interest']),('模型现金流代理',bridge['fcff_proxy'])]
    bridge_rows=''.join(f'<tr><th>{e(k)}</th><td>{bn(v)}</td></tr>' for k,v in key_rows)
    bridge_visual=''.join(f'<div class="cash-row"><span>{e(k)}</span><i style="--w:{abs(v)/bridge["cfo"]*100:.2f}%;--bar:{"#B85C40" if v<0 else "#3154D9"}"></i><b>{bn(v)}</b></div>' for k,v in key_rows[1:])
    max_value=max(price,*[x['value_per_share'] for x in case['scenarios'].values()])*1.12
    scenario_rows=''
    for name,label in [('bear','压力'),('base','基准'),('bull','乐观')]:
        val=case['scenarios'][name]
        scenario_rows+=f'<div class="scenario-row"><b>{label}</b><div class="range-track"><i style="width:{val["value_per_share"]/max_value*100:.3f}%"></i><span class="price-mark" style="left:{price/max_value*100:.3f}%"></span></div><strong>${val["value_per_share"]:.2f}</strong><span class="{"down" if val["upside_pct"]<0 else "up"}">{val["upside_pct"]:+.1f}%</span></div>'
    assumptions_rows=''
    for key,label,origin in [
        ('risk_free','无风险利率','财政部10年国债观测'),('erp','股权风险溢价','分析假设，不是市场一致预期'),('beta','Beta','分析假设，不是实时回归值'),('normalized_tax','正常化税率','分析假设，避免一次性税项'),('debt_cost_proxy','债务成本代理','TTM利息费用 / 期末账面债务'),('base_wacc','基准WACC','权益市值与账面债务加权'),('terminal_growth','永续增长','分析假设')]:
        value=format(case['assumptions'][key],'.2f') if key=='beta' else pct(case['assumptions'][key])
        assumptions_rows+=f'<tr><th>{label}</th><td>{value}</td><td>{origin}</td></tr>'
    scenario_assumptions=''.join(f'<tr><th>{label}</th><td>{pct(case["scenarios"][key]["growth"])}</td><td>{pct(case["scenarios"][key]["wacc"])}</td><td>{case["scenarios"][key]["terminal_pv_share"]:.1%}</td></tr>' for key,label in [('bear','压力'),('base','基准'),('bull','乐观')])
    sensitivity_rows=''
    ws=sorted({x['wacc'] for x in case['sensitivity']}); gs=sorted({x['terminal_growth'] for x in case['sensitivity']})
    for w in ws:
        cells=''.join(f'<td>${next(x["value"] for x in case["sensitivity"] if x["wacc"]==w and x["terminal_growth"]==g):.0f}</td>' for g in gs)
        sensitivity_rows+=f'<tr><th>{pct(w)}</th>{cells}</tr>'
    rr=case['runrate_sensitivity']
    case_html=f'''<article class="company" id="company-{e(symbol)}">
<div class="company-heading"><div><p class="caption">{e(case['issuer'])}</p><h1>{e(profile['question'])}</h1></div><div class="quote"><strong>${price:.2f}</strong><span>{e(symbol)} · USD</span><small>市场时间 {e(case['quote']['market_time_utc'])}</small></div></div>
<nav class="tabs" aria-label="研究章节"><button class="active" data-panel="note" aria-selected="true">研究结论</button><button data-panel="model" aria-selected="false">价格与假设</button><button data-panel="evidence" aria-selected="false">来源与过程</button></nav>
<section class="panel active" data-content="note"><div class="verdict"><p class="caption">先看结论</p><h2>{e(view_text)}</h2><p>{e(profile['thesis'])}</p><p class="muted">这是显式假设下的研究解释，不是已确认的用户观点、机构共识或交易指令。</p></div>
<div class="reading-grid"><div><h2>最重要的三条证据</h2><ol class="evidence-list">{evidence}</ol></div><aside class="decision"><h2>价格在要求什么</h2><p class="implied">{pct(implied) if implied is not None else '无可靠解'}</p><p>以TTM现金流为起点，固定基准WACC与永续增长，支持当前报价所需的未来五年年均现金流增长。</p><p class="muted">这是模型反推，不是市场一致预期，也不是收入增长率。</p><button class="text-button" data-goto="model">查看计算与调整假设</button><hr><b>起点会改变判断</b><p>若把最近季度年化作为敏感性起点，所需增长变为 {pct(rr['implied_growth']) if rr['implied_growth'] is not None else '未知'}。这不代表单季表现能够持续。</p></aside></div>
<section class="subsection"><h2>不同视角真正分歧在哪里</h2>{views}</section>
<section class="subsection"><h2>什么会改变这次判断</h2><div class="table-wrap"><table><thead><tr><th>观察点</th><th>怎样检查</th><th>削弱判断的情况</th></tr></thead><tbody>{watch}</tbody></table></div></section></section>
<section class="panel" data-content="model" hidden><h2>把价格判断拆开看</h2><p>情景价值只对应各自参数；没有赋予主观概率。竖线标记当前报价 ${price:.2f}。</p><div class="scenario-chart" aria-label="三个现金流情景与当前报价比较">{scenario_rows}</div>
<p class="callout">基准模型价值 ${base['value_per_share']:.2f}；其中终值占企业价值 {base['terminal_pv_share']:.1%}。终值敏感，不能把结果当成精确目标价。</p>
<div class="model-layout"><div class="controls"><h3>自己改变假设</h3><label for="cash-start">现金流起点</label><select id="cash-start"><option value="ttm">TTM：已报告的最近四季</option><option value="runrate">最近季度×4：仅作敏感性</option></select>
<label for="growth">未来五年现金流年均增长 <output id="growth-label"></output></label><input id="growth" type="range" min="0" max="60" step="0.5" value="{profile['growth']['base']*100}">
<label for="wacc">WACC <output id="wacc-label"></output></label><input id="wacc" type="range" min="7" max="15" step="0.01" value="{case['assumptions']['base_wacc']*100}">
<label for="terminal">永续增长 <output id="terminal-label"></output></label><input id="terminal" type="range" min="0" max="5" step="0.1" value="{profile['terminal_growth']*100}"><button id="reset-model">恢复基准假设</button></div>
<div class="live-result" aria-live="polite"><p>这些假设对应的每股模型价值</p><strong id="live-value"></strong><p id="live-change"></p><p id="live-growth"></p><p class="muted">修改参数是敏感性实验，不会改动来源数据。现金流增长假设已经包含未来再投资成本，不能把全部新增收入当成自由现金。</p></div></div>
<section class="subsection"><h2>先把现金流算对</h2><p>最近四季：{e(case['financial_period']['start'])} 至 {e(case['financial_period']['end'])}。下列金额单位均为亿美元。</p><div class="cash-bridge">{bridge_visual}</div><details><summary>展开原始数值、TTM公式与申报来源</summary><table>{bridge_rows}</table><pre>{e(json.dumps(case['ttm'],ensure_ascii=False,indent=2))}</pre></details>
<p class="muted">经营现金流−资本开支并非严格FCFF。本例再扣除SBC作为经济成本，加回税后净现金利息，构造FCFF代理。固定股数，不再叠加额外稀释假设；未包含租赁及少数股东等完整调整。</p></section>
<details><summary>全部假设与三种情景</summary><p>{e(profile['growth_rationale'])}</p><table><tr><th>参数</th><th>取值</th><th>来源 / 性质</th></tr>{assumptions_rows}</table><table><tr><th>情景</th><th>五年现金流增长</th><th>WACC</th><th>终值占EV</th></tr>{scenario_assumptions}</table></details>
<details><summary>WACC × 永续增长敏感性（固定基准现金流增长）</summary><div class="table-wrap"><table><tr><th>WACC / g</th>{''.join('<th>'+pct(g)+'</th>' for g in gs)}</tr>{sensitivity_rows}</table></div></details>
<details><summary>起点、股权薪酬和模型范围的限制</summary><p>TTM在高速增长时会滞后；最近季度年化又容易放大季节性和营运资本时点。本例同时呈现两者，不能把其中一项直接称作未来现金流预测。</p><p>期末净债务代理 {bn(case['balance']['net_debt'])} 亿美元；股数时点 {e(case['financial_period']['shares_date'])}，不等于报价时点实时股数。股权薪酬的经济成本处理也存在方法分歧。</p><p>本例没有硬拼同行PE或SOTP权重：缺少同期间、同口径的可比数据时，单一模型的透明性优先；因此结论仍是条件分析。</p></details></section>
<section class="panel" data-content="evidence" hidden><h2>证据、计算与人的判断各做了什么</h2><div class="process"><div><b>定义问题</b><p>从产业机会追到价格要求，而不是汇总新闻。</p></div><div><b>获取证据</b><p>公开行情、SEC XBRL和财政部利率，保留期间和指纹。</p></div><div><b>检查与计算</b><p>累积值相减得到季度，匹配期间构造TTM，再运行情景和反推。</p></div><div><b>审阅与解释</b><p>当前Codex对话结合原文辅助整理；不冒充本次全自动CLI研究成功。</p></div></div>
<h3>本次具体纠正了什么</h3><p>旧接口的直接quarter现金流停在更早季度。本次计算本季CFO为 {bn(case['quarters']['cfo']['value'])} 亿美元、资本开支 {bn(case['quarters']['capex']['value'])} 亿美元，避免混用季度与年内累计。</p><p>研究文本撰写日 {e(profile['editorial_as_of'])}；数据截止 {e(case['as_of'])}。程序重算不等于重新审阅所有商业假设。</p>
<h3>原始披露</h3><ul>{''.join(f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">{e(x["title"])}</a> · {e(x["published"])}</li>' for x in profile['sources'])}<li><a href="{e(case['source_receipt']['url'])}" target="_blank" rel="noopener noreferrer">SEC Company Facts JSON</a></li></ul>
<details><summary>计算账本与来源指纹</summary><pre>{e(json.dumps(case,ensure_ascii=False,indent=2))}</pre></details><details><summary>数据接口状态与原始运行记录</summary>{data_view.header(snapshot)}<pre>{e(json.dumps(telemetry,ensure_ascii=False,indent=2))}</pre></details><button id="download-case">下载本案例研究记录</button></section></article>'''
    other=[]
    reviews={x['id']:x for x in review['assets']}
    for key,item in snapshot['assets'].items():
        if key==symbol: continue
        summary=reviews.get(key,{}).get('candidate_thesis',{}).get('text','本页展示已取得资料，尚未形成完整研究结论。')
        other.append(f'<article class="company" id="company-{e(key)}" hidden><p class="caption">资料概览</p><h1>{e(key)}</h1><p>这个标的保留数据与原研究入口，尚未完成与完整案例同等深度的价格分析。</p>{data_view.asset(item)}<section class="subsection"><h2>原研究假设</h2><p>{e(summary)}</p><small>这是此前AI待审解释，不代表已经结合最新数据重跑。</small></section></article>')
    all_ids=[symbol,*[x for x in snapshot['assets'] if x!=symbol]]
    # An independently chosen public case can accompany a public demo without account data.
    nav=''.join(f'<a href="#company-{e(k)}" data-company="{e(k)}" class="{"selected" if k==symbol else ""}"><b>{e(k)}</b><span>{"完整案例" if k==symbol else "资料概览"}</span></a>' for k in all_ids)
    payload=json.dumps(case,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    css=(Path(__file__).parent/'report.css').read_text(encoding='utf-8')
    js=(Path(__file__).parent/'report.js').read_text(encoding='utf-8')
    scope='私人持仓工作台 · 仅本地保存' if private else '独立公开研究案例 · 不展示券商账户或持仓'
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Liam 的研究笔记 · {e(symbol)}</title><style>{css}</style></head><body>
<header class="topbar"><a href="#company-{e(symbol)}" class="brand">Liam 的研究笔记<span>把判断放到证据与价格里检验</span></a><span class="scope">{scope}</span></header><div class="workspace"><aside class="sidebar"><p>研究目录</p><nav aria-label="证券目录">{nav}</nav><div class="sidebar-note">观点有日期，假设可检查。打开本页不会自动刷新数据。</div></aside><main>{case_html}{''.join(other)}</main></div><script id="case-data" type="application/json">{payload}</script><script>{js}</script><noscript><style>.company[hidden],.panel[hidden]{{display:block!important}}.controls,.text-button{{display:none}}</style><p>JavaScript未启用；全部静态研究内容仍可阅读，互动模型不可用。</p></noscript></body></html>'''
    (output/'index.html').write_text(page,encoding='utf-8')
    u.save(output/'case-study.json',case)


def rebuild(report,review,telemetry,output,private=False):
    path=Path(output)/'case-study.json'
    if not path.exists(): return
    old=u.load(path)
    case=case_research.build(report['data_snapshot'],Path(output)/'data',old['symbol'],old['profile'])
    render(report,review,telemetry,output,case,private)
