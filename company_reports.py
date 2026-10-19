"""Company-specific research sections, sharing the report's accessible navigation."""
import html,json,re
from pathlib import Path
import company_models as models
import utilities as u

e=lambda x:html.escape(str(x))

def json_script(value):
    return json.dumps(value,ensure_ascii=False).replace('<',r'\u003c').replace('>',r'\u003e').replace('&',r'\u0026')

def fmt(value,unit):
    return f'{value*100:.1f}%' if unit=='%' else f'{value:.2f}{unit}'

def scenario_labels(model,values):
    labels={x['key']:x for x in model['controls']}
    return '；'.join(labels[k]['label']+' '+fmt(v,labels[k]['unit']) if k in labels else k+' '+str(v) for k,v in values.items())

def article(case):
    p=case['profile'];s=p['symbol'];m=p['model'];q=case['quote']
    sources={x['id']:x for x in p['sources']}
    facts=''.join(f'<li><h3>{e(f["title"])}</h3><p>{e(f["fact"])}</p><p class="interpretation">判断：{e(f["interpretation"])}</p><a href="{e(sources[f["source"]]["url"])}" target="_blank" rel="noopener noreferrer">核对原始披露</a></li>' for f in p['facts'])
    views=''.join(f'<div class="view-row"><h3>{e(v["name"])}</h3><p>{e(v["text"])}</p></div>' for v in p['views'])
    watch=''.join(f'<tr><th>{e(w["signal"])}</th><td>{e(w["test"])}</td><td>{e(w["invalidates"])}</td></tr>' for w in p['watch'])
    scen=''.join(f'<tr><th>{label}</th><td>${case["scenarios"][name]["value_per_share"]:,.2f}</td><td>{case["scenarios"][name]["upside_pct"]:+.1f}%</td><td>{e(scenario_labels(m,m["scenarios"][name]))}</td></tr>' for name,label in [('bear','压力'),('base','基准'),('bull','乐观')])
    controls=''
    for c in m['controls']:
        scale=100 if c['unit']=='%' else 1
        controls+=f'<label for="{s}-{e(c["key"])}">{e(c["label"])} <output data-label="{e(c["key"])}"></output></label><input id="{s}-{e(c["key"])}" data-key="{e(c["key"])}" data-scale="{scale}" type="range" min="{c["min"]*scale}" max="{c["max"]*scale}" step="{c["step"]*scale}" value="{m["parameters"][c["key"]]*scale}">'
    x,y=m['controls'][:2];xs=sorted({v['x'] for v in case['sensitivity']});ys=sorted({v['y'] for v in case['sensitivity']})
    matrix=''.join('<tr><th>'+fmt(a,x['unit'])+'</th>'+''.join(f'<td>${next(v["value"] for v in case["sensitivity"] if v["x"]==a and v["y"]==b):,.0f}</td>' for b in ys)+'</tr>' for a in xs)
    implied=case['implied'];implied_text=fmt(implied,m['reverse']['unit']) if implied is not None else '给定求解范围无可靠解'
    source_html=''.join(f'<li><a href="{e(z["url"])}" target="_blank" rel="noopener noreferrer">{e(z["title"])}</a> · 披露/查询日 {e(z["published"])}</li>' for z in p['sources'])
    return f'''<article class="company study" id="company-{s}" hidden>
<div class="company-heading"><div><p class="caption">{e(p['name'])}</p><h1>{e(p['question'])}</h1></div><div class="quote"><strong>${q['price']:,.2f}</strong><span>{s} · USD</span><small>市场时间 {e(q['market_time_utc'])}</small></div></div>
<nav class="tabs" aria-label="{s}研究章节"><button class="active" data-panel="note" aria-selected="true">研究结论</button><button data-panel="model" aria-selected="false">价格与假设</button><button data-panel="evidence" aria-selected="false">来源与过程</button></nav>
<section class="panel active" data-content="note"><div class="verdict"><p class="caption">本轮判断</p><h2>{e(p['verdict'])}</h2><p>{e(p['thesis'])}</p><small>研究撰写 {e(p['editorial_as_of'])}；事实、解释和未来参数分开记录。</small></div>
<div class="reading-grid"><div><h2>判断依据</h2><ol class="evidence-list">{facts}</ol></div><aside class="decision"><h2>价格要求什么</h2><p>{e(m['reverse']['label'])}</p><p class="implied">{implied_text}</p><p>{e(m['basis'])}</p><small>固定其余基准参数的程序反推，不是机构共识。</small><hr><button class="text-button" data-goto="model">查看情景与调整假设</button></aside></div>
<section class="subsection"><h2>从六个角度检查同一判断</h2>{views}</section><section class="subsection"><h2>什么会改变判断</h2><div class="table-wrap"><table><tr><th>观察点</th><th>怎样检查</th><th>失效条件</th></tr>{watch}</table></div></section></section>
<section class="panel" data-content="model" hidden><h2>{e(m['title'])}</h2><p>{e(m['basis'])}</p><p class="callout">{e(m['formula'])}</p><div class="table-wrap"><table><tr><th>情景</th><th>条件价格</th><th>相对报价</th><th>与固定参数不同的情景输入</th></tr>{scen}</table></div><p class="muted">条件价格不等于目标价；参数是分析者压力假设，没有赋予概率，也没有将不同模型排序为买卖建议。</p>
<div class="model-layout"><div class="controls">{controls}<button data-reset-study>恢复基准假设</button></div><div class="live-result" aria-live="polite"><p>这些参数对应的条件价格</p><strong data-study-value></strong><p data-study-change></p><p data-study-reverse></p><small>改变的是假设，不是历史数据。</small></div></div>
<details><summary>全部固定参数、定义与中间计算</summary><pre>{e(json.dumps({'parameters':m['parameters'],'base_calculation':case['scenarios']['base']['ledger']},ensure_ascii=False,indent=2))}</pre></details>
<details><summary>{e(x['label'])} × {e(y['label'])}敏感性</summary><div class="table-wrap"><table><tr><th>行 / 列</th>{''.join('<th>'+fmt(b,y['unit'])+'</th>' for b in ys)}</tr>{matrix}</table></div></details><section class="subsection"><h2>这套模型没有解决什么</h2><ul>{''.join('<li>'+e(z)+'</li>' for z in p['limits'])}</ul></section></section>
<section class="panel" data-content="evidence" hidden><h2>本次核对与修正</h2><p>{e(p['correction'])}</p><p>{e(p['authorship'])}</p><h3>原始披露</h3><ul>{source_html}</ul><p>公式与情景由确定性代码复算；原披露数字由本次逐家核查整理。HTTP和指纹证明取得了哪份文件，不等于全面财务审计。</p><details><summary>研究输入、来源指纹及计算记录</summary><pre>{e(json.dumps(case,ensure_ascii=False,indent=2))}</pre></details><button data-download-study>下载本标的研究记录</button></section>
<script type="application/json" class="study-data">{json_script(case)}</script></article>'''


def attach(page,snapshot,output,primary,private=False):
    path=Path(output)/'company-profiles.json'
    if not path.exists():return page
    config=u.load(path);cases={}
    for profile in config['profiles']:
        symbol=profile['symbol']
        if symbol not in snapshot['assets']:continue
        cases[symbol]=models.build(profile,snapshot['assets'][symbol]['quote'])
    if not cases:return page
    for symbol,case in cases.items():
        # Replace only the legacy company placeholder, not the primary AVGO article.
        pattern=rf'<article class="company" id="company-{re.escape(symbol)}" hidden>.*?</article>'
        page,count=re.subn(pattern,lambda _:article(case),page,flags=re.S)
        if count!=1:raise ValueError('Expected one company placeholder: '+symbol)
        page=page.replace(f'<b>{symbol}</b><span>资料概览</span>',f'<b>{symbol}</b><span>研究报告</span>')
    rows=[];portfolio_rows=[]
    for symbol,a in snapshot['assets'].items():
        if symbol==primary['symbol']:
            title=primary['profile']['question'];method='现金流情景';value=primary['scenarios']['base']['value_per_share']
        elif symbol in cases:
            c=cases[symbol];title=c['profile']['question'];method=c['profile']['model']['title'];value=c['scenarios']['base']['value_per_share']
        else:continue
        rows.append(f'<tr><th><a href="#company-{symbol}" data-company="{symbol}">{symbol}</a></th><td>{e(title)}</td><td>{e(method)}</td><td>${a["quote"]["price"]:,.2f}</td><td>${value:,.2f}</td></tr>')
        name='博通' if symbol==primary['symbol'] else cases[symbol]['profile']['name']
        portfolio_rows.append(f'<tr><th><a href="#company-{symbol}" data-company="{symbol}">{e(name)}<small>{symbol}</small></a></th><td>{e(title)}</td><td>{e(method)}</td></tr>')
    overview=f'''<article class="company overview" id="company-_overview"><p class="caption">研究总览</p><h1>先看每家公司在验证什么</h1><p>共 {len(rows)} 份研究：点击标的查看判断、原始披露、不同视角和可调整的价格实验。</p><p class="callout">不同模型回答不同问题。基准条件价格仅用于检查假设；海力士的数字是ADR溢价情景，不能与其他公司的盈利或现金流估值横向排名。</p><div class="table-wrap"><table><tr><th>标的</th><th>研究问题</th><th>分析方法</th><th>观察报价</th><th>基准条件价</th></tr>{''.join(rows)}</table></div><section class="subsection"><h2>怎样更新</h2><p>刷新接口会更新报价和程序计算，研究文字与官方披露保留原日期。新的财报需要重新核查并更新事实及假设，不能靠改时间戳冒充已读新财报。</p></section></article>'''
    if not private:
        overview=f'''<article class="company overview portfolio-overview" id="company-_overview"><p class="caption">Liam Liang · 个人项目</p><h1>从问题定义到报告交付</h1><p class="project-intro">把个人证券研究需求做成可复用的 AI 工作流。我负责问题定义、流程配置与结果核验，借助 Codex 完成实现和研究整理。</p>
<div class="project-actions"><a class="primary-action" href="#company-AVGO" data-company="AVGO">先看一份完整报告</a><a href="#company-MU" data-company="MU" data-open-panel="model">体验参数重算</a><a href="#company-CRCL" data-company="CRCL" data-open-panel="evidence">核对来源与过程</a></div>
<div class="project-proof"><div><b>把需求拆成任务</b><p>确定研究问题、证据范围、输出结构与检查条件。</p></div><div><b>连接工具完成交付</b><p>组织资料检索、公开数据接口、程序计算与报告生成。</p></div><div><b>检查结果再迭代</b><p>核对数据口径、处理失败，保留来源和假设。</p></div></div>
<section class="subsection"><h2>{len(rows)} 份研究，按业务选择分析方法</h2><p>选一家公司，可查看研究结论、调整价格假设，或展开原始披露。</p><div class="table-wrap"><table><tr><th>公司</th><th>研究问题</th><th>分析方法</th></tr>{''.join(portfolio_rows)}</table></div></section>
<details><summary>数据、更新与研究边界</summary><p>公开行情、SEC申报和公司披露均保留来源及日期；未来参数属于分析假设，不是机构共识或交易建议。海力士使用ADR报价诊断，不将其换算价称为内在价值。</p><p>刷新数据会复算结果；研究文字需要在新披露后重新核对。这里展示的是有日期的交付成果，账户金额、仓位、成本与盈亏不公开。</p></details></article>'''
        page=page.replace(f'href="#company-{primary["symbol"]}" class="brand"','href="#company-_overview" data-company="_overview" class="brand"',1)
        page=page.replace('Liam 的研究笔记<span>把判断放到证据与价格里检验</span>','Equity Research Agent<span>Liam 的 AI 工作流实践</span>',1)
        page=page.replace('公开研究报告 · 不含账户金额、仓位或成本','项目作品集 · 可交互报告',1)
    page=page.replace('<main>','<main>'+overview,1).replace(f'<article class="company" id="company-{primary["symbol"]}">',f'<article class="company" id="company-{primary["symbol"]}" hidden>')
    page=page.replace('class="selected"','class=""')
    page=page.replace(f'<title>Liam 的研究笔记 · {e(primary["symbol"])}</title>','<title>Liam 的研究笔记 · 多标的研究</title>')
    page=page.replace('<nav aria-label="证券目录">','<nav aria-label="证券目录"><a href="#company-_overview" data-company="_overview" class="selected"><b>总览</b><span>全部研究</span></a>',1)
    js=(Path(__file__).parent/'company_reports.js').read_text(encoding='utf-8')
    page=page.replace('</body>','<script>'+js+'</script></body>')
    u.save(Path(output)/'company-studies.json',{'editorial_as_of':config['editorial_as_of'],'cases':cases})
    return page
