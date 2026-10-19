import unittest
import market_data as d


class DataTests(unittest.TestCase):
    def facts(self,rows):
        return {'entityName':'Example','cik':1,'facts':{'us-gaap':{'Revenues':{'units':{'USD':rows}}}}}

    def test_ytd_not_labeled_quarter(self):
        self.assertEqual(d.period_type({'start':'2026-01-01','end':'2026-09-30'}),'year_to_date')
        self.assertEqual(d.period_type({'start':'2026-07-01','end':'2026-09-30'}),'quarter')

    def test_future_filing_excluded(self):
        data=self.facts([{'start':'2026-07-01','end':'2026-09-30','val':100,'form':'10-Q','filed':'2026-11-01'}])
        self.assertNotIn('revenue',d.normalize_facts(data,'2026-10-19')['metrics'])

    def test_most_recent_period_before_most_recent_filing(self):
        data=self.facts([
            {'start':'2026-04-01','end':'2026-06-30','val':100,'form':'10-Q','filed':'2026-08-01'},
            {'start':'2025-07-01','end':'2025-09-30','val':80,'form':'10-Q/A','filed':'2026-10-01'}])
        row=d.normalize_facts(data,'2026-10-19')['metrics']['revenue']['quarter']
        self.assertEqual(row['val'],100)

    def test_no_currency_conversion_or_unit_scaling(self):
        data={'facts':{'ifrs-full':{'Revenue':{'units':{'KRW':[{'start':'2026-01-01','end':'2026-03-31','val':123000000,'form':'20-F','filed':'2026-04-30'}]}}}}}
        row=d.normalize_facts(data,'2026-10-19')['metrics']['revenue']['quarter']
        self.assertEqual((row['val'],row['unit']),(123000000,'KRW'))

    def test_quote_symbol_mismatch(self):
        with self.assertRaises(ValueError):
            d.parse_quote({'chart':{'result':[{'meta':{'symbol':'WRONG'}}]}},'AVGO','2026-10-19')

    def test_empty_quote_is_not_zero(self):
        with self.assertRaises(ValueError): d.parse_quote({'chart':{'result':[]}},'AVGO','2026-10-19')

    def test_quote_timestamp_preserved(self):
        meta={'symbol':'AVGO','regularMarketTime':1792180801,'regularMarketPrice':328.75,'currency':'USD'}
        q=d.parse_quote({'chart':{'result':[{'meta':meta}]}},'AVGO','2026-10-19')
        self.assertEqual(q['price'],328.75)
        self.assertEqual(q['realtime_entitlement'],'not_verified')
        self.assertTrue(q['market_time_utc'].startswith('2026-10-16'))

    def test_treasury_excludes_future_observation(self):
        raw=b'<feed><properties><NEW_DATE>2026-10-16T00:00:00</NEW_DATE><BC_10YEAR>4.2</BC_10YEAR></properties><properties><NEW_DATE>2026-10-20</NEW_DATE><BC_10YEAR>4.9</BC_10YEAR></properties></feed>'
        q=d.parse_treasury(raw,'2026-10-19')
        self.assertEqual(q['date'],'2026-10-16')
        self.assertEqual(q['yields_pct']['BC_10YEAR'],4.2)

    def test_live_observations_are_available_to_ai_prompt(self):
        import showcase
        snapshot={'assets':{'AVGO':{'quote':{'status':'ok','symbol':'AVGO','provider':'Yahoo Finance chart (unofficial)','price':328.75,'currency':'USD','market_time_utc':'2026-10-16T20:00:01+00:00','source_url':'https://query1.finance.yahoo.com/v8/finance/chart/AVGO'},'fundamentals':{'status':'failed'}}},
                  'macro':{'status':'ok','date':'2026-10-16','yields_pct':{'BC_10YEAR':4.2},'source_url':'https://home.treasury.gov/'}}
        report={'as_of':'2026-10-19','question':'test','facts':[],'sources':[],'companies':[],'scope_limitations':[],'data_snapshot':snapshot}
        prompt=showcase.review_prompt(report)
        self.assertIn('api-quote-AVGO',prompt)
        self.assertIn('328.75',prompt)
        self.assertIn('api-treasury',prompt)

    def test_wrong_issuer_quote_cannot_become_zero(self):
        meta={'symbol':'AVGO','regularMarketTime':1792180801,'regularMarketPrice':float('nan'),'currency':'USD'}
        with self.assertRaises(ValueError):
            d.parse_quote({'chart':{'result':[{'meta':meta}]}},'AVGO','2026-10-19')

    def test_http_success_is_not_financial_coverage(self):
        import data_view
        snapshot={'coverage':{'assets':1,'quotes_ok':1,'companyfacts_ok':1,'treasury_ok':False},
            'assets':{'X':{'fundamentals':{'status':'ok','metrics':{}}}},
            'macro':{'status':'failed'},'fetched_at':'2026-10-19','as_of':'2026-10-19','requests':[]}
        self.assertIn('0 家有可解析财务字段 / 1 家接口返回成功',data_view.header(snapshot))


if __name__=='__main__': unittest.main()
