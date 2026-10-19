"""Present API observations separately from AI interpretations and model assumptions."""
import copy
import html
import json
import market_data as d

e=lambda x:html.escape(str(x))


def header(snapshot):
    c=snapshot['coverage']; macro=snapshot['macro']
    cards=[('Yahoo Finance / 行情',f"{c['quotes_ok']}/{c['assets']} 个标的取得报价",'公共非官方接口；显示交易时点，不保证实时订阅'),
           ('SEC EDGAR / 财报',f"{c.get('companyfacts_with_metrics',sum(bool(a['fundamentals'].get('metrics')) for a in snapshot['assets'].values()))} 家有可解析财务字段 / {c['companyfacts_ok']} 家接口返回成功",'接口成功不代表字段完整；保留币种、单位与财务期间'),
           ('US Treasury / 利率','已连接' if c['treasury_ok'] else '获取失败','官方XML；国债收益率不是WACC')]
    content=''.join(f'<article><h3>{e(k)}</h3><p>{e(v)}</p><small>{e(b)}</small></article>' for k,v,b in cards)
    rate=''
    if macro['status']=='ok':
        values=' · '.join(f'{k.replace("BC_","")} {v:g}%' for k,v in macro['yields_pct'].items())
        rate=f'<p><b>利率观测 {e(macro["date"])}</b>：{e(values)} <a href="{e(macro["source_url"])}">原始接口 ↗</a></p>'
    return f'<section id="data-status"><p class="eyebrow">CONNECTED DATA / READ ONLY</p><h2>真实数据接入状态</h2><p>接口获取：{e(snapshot["fetched_at"])} · 研究截止：{e(snapshot["as_of"])}。行情时点与财报期间分别展示；这不是刷新页面即取数。</p><div class="grid">{content}</div>{rate}<details><summary>查看实际请求状态、原始响应指纹和失败原因</summary><pre>{e(json.dumps(snapshot["requests"],ensure_ascii=False,indent=2))}</pre></details><p>行情与XBRL会进入下一轮AI证据包；仅刷新数据不会伪装为已重新完成AI分析。持仓名单来自本地快照，未自动连接券商账户。</p></section>'


def asset(item):
    q=item['quote']; f=item['fundamentals']; parts=[]
    if q['status']=='ok':
        parts.append(f'<p class="thesis"><b>{e(q["symbol"])} 报价 {q["price"]:g} {e(q["currency"])}</b><br>市场时间 {e(q["market_time_utc"])} · {e(q["exchange"])} · 非保证实时<br><small>数据距截止日 {q["observation_age_days"]} 个日历日，周末休市可能正常；实际交易状态需另核实。</small> <a href="{e(q["source_url"])}">行情JSON ↗</a></p>')
    else: parts.append(f'<p class="gap">行情获取失败：{e(q.get("error"))}。没有填0或沿用旧价冒充新价。</p>')
    if f['status']=='ok':
        rows=[]
        for key,periods in f['metrics'].items():
            for kind,row in periods.items():
                old=' · 较旧数据' if row['stale_days']>450 else ''
                rows.append(f'<tr><td>{e(d.LABELS[key])}</td><td>{e(kind)}</td><td>{row["val"]:,.0f} {e(row["unit"])}</td><td>{e(row.get("start","时点"))} → {e(row["end"])}{old}</td><td>{e(row["filed"])}</td></tr>')
        if not rows:
            parts.append('<p class="gap">SEC接口返回成功，但没有解析出支持的财务字段；不能据此视为已取得可用于分析的财报。需核对申报类型、原始报表或发行方资料。</p>')
        parts.append(f'<details><summary>查看SEC结构化财报 · {e(f["entity_name"])}</summary><p><a href="{e(f["source_url"])}">SEC companyfacts原始JSON ↗</a> · 不将年内累计冒充单季、不自动换汇或推算ADR每股值。</p><div class="scroll"><table><tr><th>项目</th><th>口径</th><th>原始数值与单位</th><th>期间</th><th>申报日期</th></tr>{"".join(rows)}</table></div><p>未匹配字段：{e("、".join(d.LABELS[k] for k in f["missing_metrics"])) or "无"}。标签未匹配不代表公司不存在该项目；净债务还需核对债务组成。</p></details>')
    else: parts.append(f'<p class="gap">财务接口：{e(f["status"])} · {e(f.get("reason",f.get("error","")))}</p>')
    return ''.join(parts)


def refresh_gaps(review,snapshot):
    """Update observable availability only. Never invent a fresh AI investment judgment."""
    review=copy.deepcopy(review); macro=snapshot['macro']
    for a in review['assets']:
        item=snapshot['assets'][a['id']]; q=item['quote']; f=item['fundamentals']
        for lens in a['lenses']:
            if lens['id']=='expectations' and q['status']=='ok':
                lens.update(finding=f"已取得{q['market_time_utc']}报价{q['price']} {q['currency']}。下一步是结合可比期间财务与明确假设，反推价格要求；报价本身不能证明便宜或贵。",
                    fact_ids=['api-quote-'+a['id']],missing_evidence=['ETF需要净值、折溢价及跟踪数据' if item['kind']=='etf' else '明确增长、利润率、再投资、折现率假设；核对股数和完整净债务；ADR需存托比例与汇率'])
            if lens['id']=='macro' and macro['status']=='ok':
                lens.update(finding=f"已取得美国财政部{macro['date']}国债曲线，10年期为{macro['yields_pct'].get('BC_10YEAR','未提供')}%。它提供折现率的基准参考，不等于企业WACC，也不单独证明行业需求方向。",
                    fact_ids=['api-treasury'],missing_evidence=['股权风险溢价、企业融资成本与产业资本开支证据'])
        if q['status']=='ok':
            a['price_assessment']={'status':'data_available_assumptions_needed','missing_inputs':[
                'ETF净值、折溢价和跟踪数据' if item['kind']=='etf' else '估值假设尚未确认；债务组成、每股映射和财务期间仍需核对']}
    review['limitations']=[x.replace('没有重新同步IBKR或刷新证券报价','未重新同步IBKR；报价与SEC数据已由独立接口刷新，原AI研究未重跑') for x in review['limitations']]
    review['limitations'].append('数据刷新只更新可观察数据及缺口状态，不代表原AI解释、投资假设或估值已经重新完成。')
    review['limitations']=list(dict.fromkeys(review['limitations']))
    return review
