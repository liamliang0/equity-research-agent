"""Build an auditable cash-flow case from aligned SEC periods, never quarter annualization."""
from datetime import date,timedelta
import json
from pathlib import Path
import math
import market_data


def rows(raw,tags,as_of):
    found={}
    for namespace in ('us-gaap','ifrs-full'):
        for tag in tags:
            for r in raw.get('facts',{}).get(namespace,{}).get(tag,{}).get('units',{}).get('USD',[]):
                if not r.get('start') or not r.get('filed') or r['filed']>as_of or r['end']>as_of: continue
                if r.get('form') not in ('10-Q','10-Q/A','10-K','10-K/A','20-F'): continue
                if not isinstance(r.get('val'),(int,float)) or not math.isfinite(r['val']): continue
                key=(r['start'],r['end'])
                item=dict(r,tag=tag,namespace=namespace,unit='USD')
                if key not in found or r['filed']>found[key]['filed']: found[key]=item
    return list(found.values())


def ttm(values,anchor=None):
    """Prior FY + current YTD - comparable prior YTD, all identical metric units."""
    if not values: raise ValueError('Missing SEC metric')
    end=anchor or max(r['end'] for r in values)
    current=[r for r in values if r['end']==end and market_data.period_type(r) in ('annual','year_to_date')]
    if not current: raise ValueError('No annual or cumulative observation at the common anchor')
    c=max(current,key=lambda r:((date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days,r['filed']))
    if market_data.period_type(c)=='annual':
        return {'value':c['val'],'start':c['start'],'end':end,'formula':'reported annual','inputs':[c]}
    previous_end=(date.fromisoformat(c['start'])-timedelta(days=1)).isoformat()
    annual=[r for r in values if r['end']==previous_end and market_data.period_type(r)=='annual']
    if not annual: raise ValueError('Prior fiscal year missing; do not annualize YTD')
    a=max(annual,key=lambda r:r['filed'])
    duration=(date.fromisoformat(c['end'])-date.fromisoformat(c['start'])).days
    prior=[r for r in values if r['start']==a['start'] and abs((date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days-duration)<=8 and r['end']<a['end']]
    if not prior: raise ValueError('Comparable prior YTD missing')
    p=min(prior,key=lambda r:abs((date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days-duration))
    return {'value':a['val']+c['val']-p['val'],'start':(date.fromisoformat(p['end'])+timedelta(days=1)).isoformat(),'end':end,
            'formula':'prior fiscal year + current YTD - prior comparable YTD','inputs':[a,c,p]}


def last_quarter(values,anchor):
    direct=[r for r in values if r['end']==anchor and market_data.period_type(r)=='quarter']
    if direct:
        r=max(direct,key=lambda r:r['filed']); return {'value':r['val'],'start':r['start'],'end':anchor,'formula':'reported quarter','inputs':[r]}
    cumulative=[r for r in values if r['end']==anchor and market_data.period_type(r)=='year_to_date']
    if not cumulative: raise ValueError('Quarter cannot be derived')
    c=max(cumulative,key=lambda r:r['filed'])
    prior=[r for r in values if r['start']==c['start'] and 70<=(date.fromisoformat(anchor)-date.fromisoformat(r['end'])).days<=110]
    if not prior: raise ValueError('Prior cumulative quarter missing')
    p=max(prior,key=lambda r:r['end'])
    return {'value':c['val']-p['val'],'start':(date.fromisoformat(p['end'])+timedelta(days=1)).isoformat(),'end':anchor,'formula':'current YTD - previous YTD','inputs':[c,p]}


def cash_dcf(cash,debt,shares,growth,wacc,terminal):
    vals=(cash,debt,shares,growth,wacc,terminal)
    if not all(math.isfinite(x) for x in vals) or cash<=0 or shares<=0 or not -.5<=growth<=1 or not 0<=terminal<wacc<.5:
        raise ValueError('Invalid cash-flow assumptions')
    years=[{'year':i,'cash_flow':cash*(1+growth)**i,'pv':cash*(1+growth)**i/(1+wacc)**i} for i in range(1,6)]
    tv=years[-1]['cash_flow']*(1+terminal)/(wacc-terminal)/(1+wacc)**5
    ev=sum(x['pv'] for x in years)+tv
    return {'value_per_share':max(0,ev-debt)/shares,'enterprise_value':ev,'terminal_pv_share':tv/ev,'years':years}


def reverse_growth(cash,debt,shares,price,wacc,terminal):
    lo,hi=-.5,1.
    value=lambda g:cash_dcf(cash,debt,shares,g,wacc,terminal)['value_per_share']
    if not value(lo)<=price<=value(hi): return None
    for _ in range(90):
        mid=(lo+hi)/2
        if value(mid)<price: lo=mid
        else: hi=mid
    return (lo+hi)/2


def build(snapshot,data_dir,symbol,profile):
    a=snapshot['assets'][symbol]
    if a['kind']!='equity' or a['quote']['status']!='ok' or a['quote']['currency']!='USD':
        raise ValueError('Complete case currently requires a USD ordinary equity with a verified quote')
    receipt=next(x for x in snapshot['requests'] if x.get('asset')==symbol and x.get('adapter')=='sec_companyfacts' and x['status']=='ok')
    raw=json.loads((Path(data_dir)/'raw'/(receipt['sha256']+'.raw')).read_text(encoding='utf-8'))
    as_of=snapshot['as_of']
    definitions={'revenue':market_data.TAGS['revenue'],'cfo':market_data.TAGS['operating_cash_flow'],'capex':market_data.TAGS['capex'],
        'sbc':market_data.TAGS['sbc'],'interest':['InterestPaidNet'],'interest_expense':['InterestExpense','InterestExpenseNonoperating','InterestExpenseNonOperating']}
    series={k:rows(raw,tags,as_of) for k,tags in definitions.items()}
    anchor=max(r['end'] for r in series['cfo'] if market_data.period_type(r) in ('annual','year_to_date'))
    calc={k:ttm(v,anchor) for k,v in series.items()}
    quarters={k:last_quarter(series[k],anchor) for k in ('revenue','cfo','capex','sbc','interest')}
    metrics=a['fundamentals']['metrics']
    cash=metrics['cash']['instant']; current=metrics['debt_current']['instant']; noncurrent=metrics['debt_noncurrent']['instant']; stock=metrics['shares']['instant']
    if {cash['end'],current['end'],noncurrent['end']}!={anchor}: raise ValueError('Debt and cash balance sheet dates do not align with cash-flow anchor')
    if any(x['unit']!='USD' for x in (cash,current,noncurrent)): raise ValueError('Unconverted balance sheet currency')
    shares=stock['val']; debt=current['val']+noncurrent['val']; net_debt=debt-cash['val']; price=a['quote']['price']
    tax=profile['tax_assumption']
    # Treat SBC as an economic cash cost; do not also model extra dilution on top.
    fcf=calc['cfo']['value']-calc['capex']['value']
    fcff_proxy=fcf-calc['sbc']['value']+calc['interest']['value']*(1-tax)
    if fcff_proxy<=0: raise ValueError('Nonpositive proxy requires a different model')
    rf=snapshot['macro']['yields_pct']['BC_10YEAR']/100
    equity_cost=rf+profile['beta_assumption']*profile['erp_assumption']
    debt_cost=calc['interest_expense']['value']/debt
    market_cap=price*shares
    wacc=round(equity_cost*market_cap/(market_cap+debt)+debt_cost*(1-tax)*debt/(market_cap+debt),4)
    assumptions={'risk_free':rf,'erp':profile['erp_assumption'],'beta':profile['beta_assumption'],'normalized_tax':tax,
        'debt_cost_proxy':debt_cost,'base_wacc':wacc,'terminal_growth':profile['terminal_growth'],
        'note':'ERP, beta, normalized tax, cash-flow growth and terminal growth are explicit analyst assumptions, not consensus. Debt cost uses TTM expense / period-end book debt. WACC uses market equity + book debt.'}
    scenarios={}
    for name,shift,growth in [('bear',.012,profile['growth']['bear']),('base',0,profile['growth']['base']),('bull',-.01,profile['growth']['bull'])]:
        v=cash_dcf(fcff_proxy,net_debt,shares,growth,wacc+shift,profile['terminal_growth'])
        scenarios[name]=dict(v,growth=growth,wacc=wacc+shift,upside_pct=(v['value_per_share']/price-1)*100)
    implied=reverse_growth(fcff_proxy,net_debt,shares,price,wacc,profile['terminal_growth'])
    runrate_proxy=4*(quarters['cfo']['value']-quarters['capex']['value']-quarters['sbc']['value']+quarters['interest']['value']*(1-tax))
    runrate_implied=reverse_growth(runrate_proxy,net_debt,shares,price,wacc,profile['terminal_growth'])
    sensitivity=[{'wacc':wacc+dw,'terminal_growth':tg,'value':cash_dcf(fcff_proxy,net_debt,shares,profile['growth']['base'],wacc+dw,tg)['value_per_share']}
                 for dw in (-.01,-.005,0,.005,.01) for tg in (.02,.025,.03,.035,.04) if wacc+dw>tg]
    return {'symbol':symbol,'as_of':as_of,'issuer':a['fundamentals']['entity_name'],'quote':a['quote'],'profile':profile,
        'financial_period':{'start':calc['cfo']['start'],'end':anchor,'shares_date':stock['end']},'ttm':calc,'quarters':quarters,
        'bridge':{'cfo':calc['cfo']['value'],'capex':calc['capex']['value'],'company_fcf_proxy':fcf,'sbc':calc['sbc']['value'],
                  'after_tax_cash_interest':calc['interest']['value']*(1-tax),'fcff_proxy':fcff_proxy},
        'balance':{'gross_debt':debt,'cash':cash['val'],'net_debt':net_debt,'shares':shares,'market_cap':market_cap,'enterprise_value':market_cap+net_debt},
        'assumptions':assumptions,'scenarios':scenarios,'implied_growth':implied,'sensitivity':sensitivity,
        'runrate_sensitivity':{'cash_proxy':runrate_proxy,'implied_growth':runrate_implied,'base_value':cash_dcf(runrate_proxy,net_debt,shares,profile['growth']['base'],wacc,profile['terminal_growth'])['value_per_share'],
            'boundary':'Latest quarter multiplied by four is only a starting-point sensitivity, not a forecast. Working capital, timing and seasonality can make it misleading.'},
        'baseline_fcf_multiple':(market_cap+net_debt)/fcff_proxy,'baseline_cash_yield':fcff_proxy/(market_cap+net_debt),
        'source_receipt':receipt,
        'boundary':'FCFF proxy = CFO - capex - SBC + after-tax net cash interest. Not GAAP FCFF or a formal target price. Starting CFO includes working-capital movements. Cash-flow growth is after reinvestment; fixed shares with SBC treated as a cost. Lease/noncontrolling adjustments and peer/SOTP valuation are not included. No buy/sell action.'}
