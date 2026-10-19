"""Read-only public data adapters: SEC XBRL, Treasury XML and Yahoo chart.

No API keys, brokerage credentials or trading functions. Yahoo is an unofficial,
best-effort interface; missing/delayed/stale values must never become zeros.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import quote
import utilities as u

UA='EquityResearchAgent/0.3 public-data-client'
TICKERS='https://www.sec.gov/files/company_tickers.json'
TAGS={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','Revenues','Revenue','SalesRevenueNet'],
 'operating_income':['OperatingIncomeLoss','ProfitLossFromOperatingActivities'],
 'net_income':['NetIncomeLoss','ProfitLoss','NetIncomeLossAvailableToCommonStockholdersBasic'],
 'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities','CashFlowsFromUsedInOperatingActivities'],
 'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PurchaseOfPropertyPlantAndEquipment'],
 'cash':['CashAndCashEquivalentsAtCarryingValue','CashAndCashEquivalents'],
 'debt_current':['LongTermDebtCurrent','LongTermDebtAndCapitalLeaseObligationsCurrent'],
 'debt_noncurrent':['LongTermDebtNoncurrent','LongTermDebtAndCapitalLeaseObligationsNoncurrent'],
 'shares':['EntityCommonStockSharesOutstanding','CommonStockSharesOutstanding'],
 'sbc':['ShareBasedCompensation','StockBasedCompensation']}
LABELS={'revenue':'收入','operating_income':'经营利润','net_income':'净利润','operating_cash_flow':'经营现金流','capex':'购置固定资产现金支出','cash':'现金及等价物','debt_current':'流动长期债务','debt_noncurrent':'非流动长期债务','shares':'已发行普通股数','sbc':'股权薪酬'}


def fetch(url, cache):
    """At most two attempts; no stale cache silently promoted to fresh data."""
    cache=Path(cache); cache.mkdir(parents=True,exist_ok=True)
    started=u.now()
    for attempt in range(2):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json,application/xml,text/xml,*/*'})
            with urllib.request.urlopen(req,timeout=18) as response:
                raw=response.read(26000001)
                if len(raw)>26000000: raise ValueError('Response exceeds 26 MB')
                digest=hashlib.sha256(raw).hexdigest()
                (cache/(digest+'.raw')).write_bytes(raw)
                return raw,{'url':url,'fetched_at':started,'http_status':response.status,'sha256':digest,'attempts':attempt+1}
        except (urllib.error.URLError,TimeoutError,ValueError) as err:
            if attempt==0: time.sleep(.5)
            else: raise RuntimeError(f'{type(err).__name__}: {err}') from err


def period_type(row):
    if not row.get('start'): return 'instant'
    days=(date.fromisoformat(row['end'])-date.fromisoformat(row['start'])).days+1
    if 70<=days<=110: return 'quarter'
    if 330<=days<=380: return 'annual'
    if 110<days<330: return 'year_to_date'
    return 'other_duration'


def normalize_facts(data, as_of):
    records={}
    for key,tags in TAGS.items():
        candidates=[]
        for namespace,concepts in data.get('facts',{}).items():
            if namespace not in ('us-gaap','ifrs-full','dei'): continue
            for tag in tags:
                for unit,rows in concepts.get(tag,{}).get('units',{}).items():
                    if key=='shares' and unit!='shares': continue
                    if key!='shares' and (len(unit)!=3 or not unit.isupper()): continue
                    for row in rows:
                        if not row.get('filed') or row['filed']>as_of or row.get('end','9999')>as_of: continue
                        if row.get('form') not in ('10-Q','10-Q/A','10-K','10-K/A','20-F','20-F/A','40-F','6-K','F-1','F-1/A'): continue
                        if not isinstance(row.get('val'),(int,float)) or isinstance(row.get('val'),bool) or not math.isfinite(row['val']): continue
                        candidates.append(dict(row,unit=unit,tag=tag,namespace=namespace,period_type=period_type(row)))
        # Keep quarter, YTD, annual and balance sheet separately. Never annualize YTD as a quarter.
        by_period={}
        for kind in ('instant','quarter','year_to_date','annual'):
            pool=[x for x in candidates if x['period_type']==kind]
            if pool:
                chosen=max(pool,key=lambda x:(x['end'],x['filed'],x.get('accn','')))
                chosen['stale_days']=(date.fromisoformat(as_of)-date.fromisoformat(chosen['end'])).days
                chosen['provenance']='SEC companyfacts; filed standard taxonomy; no currency conversion'
                by_period[kind]=chosen
        if by_period: records[key]=by_period
    return {'entity_name':data.get('entityName'),'cik':data.get('cik'),'metrics':records,
            'missing_metrics':[k for k in TAGS if k not in records],
            'boundary':'Filed data, not guidance. Quarter/YTD/annual are separate. Tags differ by issuer; net debt and ADR per-share values are not inferred.'}


def parse_quote(data,symbol,as_of):
    chart=data.get('chart',{})
    if chart.get('error') or not chart.get('result'): raise ValueError('Quote response has no result')
    item=chart['result'][0]; meta=item['meta']
    if meta.get('symbol','').upper()!=symbol.upper(): raise ValueError('Quote symbol mismatch')
    stamp=meta.get('regularMarketTime'); value=meta.get('regularMarketPrice')
    if not stamp or not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0 or not meta.get('currency'):
        raise ValueError('Price, currency or market timestamp missing')
    at=datetime.fromtimestamp(stamp,timezone.utc)
    if at.date()>date.fromisoformat(as_of): raise ValueError('Market observation is later than requested as_of')
    return {'symbol':meta['symbol'],'price':value,'currency':meta['currency'],
            'market_time_utc':at.isoformat(),'exchange':meta.get('exchangeName'),
            'exchange_timezone':meta.get('exchangeTimezoneName'),
            'observation_age_days':(date.fromisoformat(as_of)-at.date()).days,
            'provider':'Yahoo Finance chart (unofficial)', 'realtime_entitlement':'not_verified',
            'boundary':'Last reported regular-session price; not guaranteed real time. Weekend/holiday age is not itself a feed failure.'}


def parse_treasury(raw,as_of):
    root=ET.fromstring(raw)
    rows=[]
    for properties in root.iter():
        if properties.tag.rsplit('}',1)[-1]!='properties': continue
        fields={x.tag.rsplit('}',1)[-1]:x.text for x in properties}
        stamp=(fields.get('NEW_DATE') or '')[:10]
        if not stamp or stamp>as_of: continue
        yields={k:float(v) for k,v in fields.items() if k in ('BC_3MONTH','BC_2YEAR','BC_10YEAR','BC_30YEAR') and v}
        if yields: rows.append({'date':stamp,'yields_pct':yields})
    if not rows: raise ValueError('No Treasury observation on/before as_of')
    result=max(rows,key=lambda x:x['date'])
    result['boundary']='Treasury par yields in percent. A 10-year yield is a risk-free-rate reference, not WACC or a market outlook.'
    return result


def collect(assets,output,as_of=None):
    as_of=as_of or datetime.now(u.TZ).date().isoformat()
    output=Path(output).resolve(); cache=output/'raw'; output.mkdir(parents=True,exist_ok=True)
    result={'as_of':as_of,'fetched_at':u.now(),'assets':{},'macro':{},'requests':[],
            'brokerage_access':False,'positions_sync':'not_performed; input watchlist only'}
    mapping={}
    if any(a['kind']!='etf' and not a.get('sec_cik') for a in assets):
        try:
            raw,receipt=fetch(TICKERS,cache); result['requests'].append(dict(receipt,adapter='sec_ticker_map',status='ok'))
            mapping={v['ticker'].upper():str(v['cik_str']).zfill(10) for v in json.loads(raw).values()}
        except Exception as err:
            result['requests'].append({'adapter':'sec_ticker_map','url':TICKERS,'status':'failed','error':str(err)})
    macro_url=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={as_of[:4]}'
    try:
        raw,receipt=fetch(macro_url,cache)
        result['macro']=dict(parse_treasury(raw,as_of),source_url=macro_url,status='ok')
        result['requests'].append(dict(receipt,adapter='treasury',status='ok'))
    except Exception as err:
        result['macro']={'status':'failed','error':str(err),'source_url':macro_url}
    def one(a):
        key=a['id']; item={'id':key,'kind':a['kind']}; receipts=[]
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(key,safe="")}?interval=1d&range=5d'
        try:
            raw,receipt=fetch(url,cache)
            item['quote']=dict(parse_quote(json.loads(raw),key,as_of),source_url=url,status='ok')
            receipts.append(dict(receipt,adapter='yahoo_chart',asset=key,status='ok'))
        except Exception as err:
            item['quote']={'status':'failed','error':str(err),'source_url':url}
            receipts.append({'adapter':'yahoo_chart','asset':key,'url':url,'status':'failed','error':str(err)})
        cik=str(a['sec_cik']).zfill(10) if a.get('sec_cik') else mapping.get(key)
        if a['kind']=='etf':
            item['fundamentals']={'status':'not_applicable','reason':'ETF: needs issuer NAV, holdings and tracking data, not company XBRL'}
        elif not cik:
            item['fundamentals']={'status':'unmapped','reason':'No exact ticker in SEC map; no guessed issuer or ADR conversion'}
        else:
            url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
            try:
                identity_url=f'https://data.sec.gov/submissions/CIK{cik}.json'
                identity_raw,identity_receipt=fetch(identity_url,cache)
                identity=json.loads(identity_raw)
                if key not in [x.upper() for x in identity.get('tickers',[])]:
                    raise ValueError('SEC submissions ticker does not match this configured security')
                receipts.append(dict(identity_receipt,adapter='sec_identity',asset=key,status='ok'))
                raw,receipt=fetch(url,cache)
                item['fundamentals']=dict(normalize_facts(json.loads(raw),as_of),status='ok',source_url=url)
                receipts.append(dict(receipt,adapter='sec_companyfacts',asset=key,status='ok'))
            except Exception as err:
                item['fundamentals']={'status':'failed','error':str(err),'source_url':url}
                receipts.append({'adapter':'sec_companyfacts','asset':key,'url':url,'status':'failed','error':str(err)})
        return key,item,receipts
    # Two workers keep SEC requests comfortably below its published rate limit.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for key,item,receipts in pool.map(one,assets):
            result['assets'][key]=item; result['requests'].extend(receipts)
    result['coverage']={'assets':len(assets),'quotes_ok':sum(a['quote']['status']=='ok' for a in result['assets'].values()),
        'companyfacts_ok':sum(a['fundamentals']['status']=='ok' for a in result['assets'].values()),
        'companyfacts_with_metrics':sum(a['fundamentals']['status']=='ok' and bool(a['fundamentals'].get('metrics')) for a in result['assets'].values()),
        'treasury_ok':result['macro']['status']=='ok'}
    u.save(output/'data-snapshot.json',result)
    print('Data adapters: '+json.dumps(result['coverage']),flush=True)
    return result


def evidence(snapshot):
    """Give the model typed API observations with stable references, not just decorative badges."""
    facts=[]; sources={}
    for key,item in snapshot['assets'].items():
        q=item['quote']; f=item['fundamentals']
        if q['status']=='ok':
            sid='api-quote-'+key
            sources[sid]={'id':sid,'url':q['source_url'],'title':q['provider']}
            facts.append({'id':sid,'company':key,'claim':f"{q['symbol']} last regular-session quote {q['price']} {q['currency']} at {q['market_time_utc']}; real-time status not verified.",'source_ids':[sid],'audit':'structured_api_observation'})
        if f['status']=='ok':
            sid='api-sec-'+key
            sources[sid]={'id':sid,'url':f['source_url'],'title':'SEC companyfacts / '+str(f['entity_name'])}
            for metric,periods in f['metrics'].items():
                for kind,row in periods.items():
                    facts.append({'id':f'{sid}-{metric}-{kind}','company':key,
                        'claim':f"{LABELS[metric]} {row['val']} {row['unit']}; {kind} {row.get('start','instant')} to {row['end']}; filed {row['filed']}; {row['namespace']}:{row['tag']}; accession {row.get('accn')}. No unit/currency conversion.",
                        'source_ids':[sid],'audit':'structured_api_observation'})
    macro=snapshot['macro']
    if macro['status']=='ok':
        sid='api-treasury'
        sources[sid]={'id':sid,'url':macro['source_url'],'title':'US Treasury daily par yield curve'}
        facts.append({'id':sid,'company':'*','claim':f"Treasury {macro['date']} par yields, percent: {json.dumps(macro['yields_pct'])}. Not WACC.",'source_ids':[sid],'audit':'structured_api_observation'})
    return facts,sources


if __name__=='__main__':
    import argparse
    import research_agent as r
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--watchlist',type=Path,default=Path(__file__).parent/'watchlist.example.json')
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'output'/'data')
    p.add_argument('--as-of')
    a=p.parse_args()
    collect(r.load_watchlist(a.watchlist),a.output,a.as_of)
