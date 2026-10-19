"""Explicit-assumption FCFF DCF, reverse growth and sensitivity. No guessed inputs."""
from copy import deepcopy
import math


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a financial input')
    n = float(value)
    if not math.isfinite(n):
        raise ValueError('Non-finite financial input')
    return n


def validate(data):
    if data['kind'] != 'equity':
        raise ValueError('This model requires ordinary equity; ETF/ADR need a separate model or explicit conversion')
    if not data['currency'] or not data['unit'] or not data['provenance']:
        raise ValueError('Currency, consistent financial unit and provenance are required')
    if not data.get('synthetic') and (not data.get('price_as_of') or not data.get('financial_period')):
        raise ValueError('Real inputs require price_as_of and financial_period; input provenance is not automatically audited')
    for key in ('revenue', 'shares', 'price', 'net_debt'):
        number(data[key])
    if min(number(data[k]) for k in ('revenue', 'shares', 'price')) <= 0:
        raise ValueError('Revenue, shares and price must be positive')
    # Revenue / debt use the same currency unit, shares the same count scale.
    for name in ('bear', 'base', 'bull'):
        s = data['scenarios'][name]
        for key in ('growth', 'ebit_margin', 'tax_rate', 'da_ratio', 'capex_ratio', 'nwc_ratio', 'wacc', 'terminal_growth', 'terminal_roic'):
            number(s[key])
        if not -0.95 < s['growth'] < 2 or not 0 < s['wacc'] < 1 or not 0 <= s['terminal_growth'] < s['wacc']:
            raise ValueError('Unsupported growth or WACC <= terminal growth')
        if not 0 <= s['tax_rate'] < 1 or not 0 < s['terminal_roic'] <= 1 or s['terminal_growth'] >= s['terminal_roic']:
            raise ValueError('Invalid tax or terminal reinvestment assumption')
        if not 0 < s['ebit_margin'] <= 1 or any(not 0 <= s[k] <= 1 for k in ('da_ratio','capex_ratio','nwc_ratio')):
            raise ValueError('Invalid operating assumptions')
    return data


def dcf(data, scenario):
    s = scenario
    revenue = number(data['revenue'])
    pv = 0.0
    years = []
    for year in range(1, 6):
        previous = revenue
        revenue *= 1 + s['growth']
        nopat = revenue * s['ebit_margin'] * (1 - s['tax_rate'])
        fcff = nopat + revenue * s['da_ratio'] - revenue * s['capex_ratio'] - (revenue - previous) * s['nwc_ratio']
        discounted = fcff / (1 + s['wacc']) ** year
        pv += discounted
        years.append({'year': year, 'revenue': revenue, 'fcff': fcff, 'discounted_fcff': discounted})
    # Stable terminal FCFF ties growth to reinvestment, instead of extrapolating peak FCF.
    terminal_nopat = revenue * (1 + s['terminal_growth']) * s['ebit_margin'] * (1 - s['tax_rate'])
    terminal_fcff = terminal_nopat * (1 - s['terminal_growth'] / s['terminal_roic'])
    terminal_pv = terminal_fcff / (s['wacc'] - s['terminal_growth']) / (1 + s['wacc']) ** 5
    enterprise = pv + terminal_pv
    equity = enterprise - number(data['net_debt'])
    fair = max(0.0, equity) / number(data['shares'])
    if not all(math.isfinite(v) for v in (enterprise, equity, fair)):
        raise ValueError('Non-finite model result')
    return {'value_per_share': fair, 'upside_pct': (fair / data['price'] - 1) * 100,
            'enterprise_value': enterprise, 'equity_value_before_floor': equity,
            'terminal_pv_share': terminal_pv / enterprise if enterprise else None, 'years': years}


def evaluate(data):
    validate(data)
    scenarios = {k: dcf(data, v) for k, v in data['scenarios'].items()}
    base = data['scenarios']['base']
    lo, hi = -0.5, 1.0
    def price(g):
        return dcf(data, dict(base, growth=g))['value_per_share']
    # A root only has meaning if price is bracketed and the chosen model is monotonic.
    samples = [price(lo + (hi-lo)*i/20) for i in range(21)]
    monotonic = all(a <= b for a,b in zip(samples,samples[1:]))
    implied = None
    if monotonic and samples[0] <= data['price'] <= samples[-1]:
        for _ in range(80):
            mid = (lo + hi) / 2
            if price(mid) < data['price']: lo = mid
            else: hi = mid
        implied = (lo + hi) / 2
    grid = []
    for w in (base['wacc']-.01, base['wacc'], base['wacc']+.01):
        for g in (max(0,base['terminal_growth']-.005),base['terminal_growth'],base['terminal_growth']+.005):
            valid = 0 < w < 1 and 0 <= g < min(w,base['terminal_roic'])
            grid.append({'wacc':w,'terminal_growth':g,'value_per_share':dcf(data,dict(base,wacc=w,terminal_growth=g))['value_per_share'] if valid else None})
    return {'input':deepcopy(data), 'scenarios':scenarios, 'sensitivity':grid,
            'implied_five_year_growth':implied,
            'reverse_status':'solved' if implied is not None else 'unbracketed_or_nonmonotonic',
            'boundary':'Conditional model output, not market consensus or a recommendation. Fixed margins, share count and annual growth; no probability weighting. Terminal growth requires reinvestment. Cyclicals require normalized assumptions.'}
