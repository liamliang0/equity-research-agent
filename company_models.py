"""Explicit conditional pricing experiments; never consensus estimates or trade signals."""
import math


def evaluate(model, overrides=None):
    p=dict(model['parameters']);p.update(overrides or {})
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in p.values()):
        raise ValueError('All model inputs must be finite numbers')
    kind=model['kind']
    if kind=='earnings':
        if p['eps']<=0 or p['factor']<0 or p['pe']<=0 or p['discount']<0 or p['years']<0:raise ValueError('Invalid earnings assumptions')
        earnings=p['eps']*p['factor']
        value=earnings*p['pe']/(1+p['discount'])**p['years']
        ledger={'annual_eps_anchor':p['eps'],'earnings_factor':p['factor'],'scenario_eps':earnings,'pe_assumption':p['pe'],'discount_years':p['years']}
    elif kind=='growth_profit':
        if p['revenue']<=0 or p['shares']<=0 or p['dilution']<1 or not 0<=p['margin']<=1 or p['growth']<=-1 or p['pe']<=0 or p['discount']<0:raise ValueError('Invalid operating assumptions')
        revenue=p['revenue']*(1+p['growth'])**p['years']
        profit=revenue*p['margin'];shares=p['shares']*p['dilution']
        value=profit/shares*p['pe']/(1+p['discount'])**p['years']
        ledger={'scenario_annual_revenue':revenue,'post_tax_post_interest_net_margin':p['margin'],'scenario_net_profit':profit,'assumed_diluted_shares':shares,'years':p['years']}
    elif kind=='circle':
        if p['shares']<=0 or p['dilution']<1 or not 0<=p['retention']<=1 or not 0<=p['tax']<1 or p['balance_growth']<=-1 or p['yield_factor']<0 or p['discount']<0 or p['pe']<=0:raise ValueError('Invalid reserve economics')
        reserve=p['reserve_income']*(1+p['balance_growth'])**p['years']*p['yield_factor']
        other=p['other_income']*(1+p['other_growth'])**p['years']
        retained=(reserve+other)*p['retention']
        opex=p['opex']*(1+p['opex_growth'])**p['years']
        profit=max(0,retained-opex)*(1-p['tax'])
        value=profit/(p['shares']*p['dilution'])*p['pe']/(1+p['discount'])**p['years']
        ledger={'scenario_reserve_income':reserve,'scenario_other_revenue':other,'net_revenue_after_distribution':retained,'scenario_gaap_opex':opex,'scenario_after_tax_profit':profit,'assumed_diluted_shares':p['shares']*p['dilution']}
    elif kind=='adr':
        if p['local_price']<=0 or p['fx']<=0 or p['ordinary_per_ads']<=0 or p['premium']<=-1:raise ValueError('Invalid ADR conversion')
        parity=p['local_price']/p['fx']*p['ordinary_per_ads']
        value=parity*(1+p['premium'])
        ledger={'local_price_krw':p['local_price'],'krw_per_usd':p['fx'],'ordinary_per_ads':p['ordinary_per_ads'],'parity_usd':parity,'assumed_adr_premium':p['premium']}
    else:raise ValueError('Unknown model type')
    return {'value_per_share':value,'ledger':ledger,'parameters':p}


def reverse(model,price):
    """Solve one named assumption, holding all others fixed. No reliable bracket => None."""
    key=model['reverse']['key'];lo,hi=model['reverse']['range']
    if not evaluate(model,{key:lo})['value_per_share']<=price<=evaluate(model,{key:hi})['value_per_share']:return None
    for _ in range(90):
        mid=(lo+hi)/2
        if evaluate(model,{key:mid})['value_per_share']<price:lo=mid
        else:hi=mid
    return (lo+hi)/2


def build(profile,quote):
    if quote.get('status')!='ok' or quote.get('currency')!='USD':raise ValueError('A dated USD quote is required')
    result={name:dict(evaluate(profile['model'],params),upside_pct=(evaluate(profile['model'],params)['value_per_share']/quote['price']-1)*100) for name,params in profile['model']['scenarios'].items()}
    controls=profile['model']['controls']
    x,y=controls[0],controls[1]
    xs=[x['min']+(x['max']-x['min'])*i/4 for i in range(5)]
    ys=[y['min']+(y['max']-y['min'])*i/4 for i in range(5)]
    grid=[{'x':a,'y':b,'value':evaluate(profile['model'],{x['key']:a,y['key']:b})['value_per_share']} for a in xs for b in ys]
    return {'symbol':profile['symbol'],'profile':profile,'quote':quote,'scenarios':result,'implied':reverse(profile['model'],quote['price']),'sensitivity':grid,
            'boundary':'Conditional pricing experiment, not consensus, recommendation, audited valuation or a probability-weighted forecast. Editorial facts are dated and are not automatically refreshed by quote changes.'}
