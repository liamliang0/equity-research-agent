import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import os
import valuation as v
import showcase as s


class ValuationTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((Path(__file__).parent/'examples'/'valuation-assumptions.json').read_text())

    def test_constant_perpetuity_identity(self):
        # No growth or working-capital changes, D&A equals capex -> EV = NOPAT / WACC.
        p=self.data
        z=dict(p['scenarios']['base'],growth=0,terminal_growth=0,da_ratio=.03,capex_ratio=.03)
        result=v.dcf(p,z)
        expected=(1000*.20*.75/.10-200)/100
        self.assertAlmostEqual(result['value_per_share'],expected)

    def test_reverse_growth_round_trip(self):
        self.data['price']=v.dcf(self.data,self.data['scenarios']['base'])['value_per_share']
        self.assertAlmostEqual(v.evaluate(self.data)['implied_five_year_growth'],.12,places=8)

    def test_more_debt_lowers_per_share_value(self):
        before=v.evaluate(self.data)['scenarios']['base']['value_per_share']
        self.data['net_debt']+=100
        self.assertAlmostEqual(before-v.evaluate(self.data)['scenarios']['base']['value_per_share'],1)

    def test_invalid_terminal_spread(self):
        self.data['scenarios']['base']['terminal_growth']=.10
        with self.assertRaises(ValueError): v.evaluate(self.data)

    def test_missing_debt_is_not_zero(self):
        del self.data['net_debt']
        with self.assertRaises(KeyError): v.evaluate(self.data)

    def test_reject_etf_and_adr(self):
        for kind in ('etf','adr'):
            self.data['kind']=kind
            with self.assertRaises(ValueError): v.evaluate(self.data)

    def test_reject_nonfinite(self):
        self.data['shares']=float('nan')
        with self.assertRaises(ValueError): v.evaluate(self.data)

    def test_higher_discount_lowers_value(self):
        out=v.evaluate(self.data)
        grid=out['sensitivity']
        self.assertGreater(grid[1]['value_per_share'],grid[7]['value_per_share'])

    def test_unbracketed_does_not_invent_answer(self):
        self.data['price']=1e9
        self.assertIsNone(v.evaluate(self.data)['implied_five_year_growth'])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.report={'as_of':'2026-10-19','facts':[{'id':'f','company':'A'}],'companies':[{'id':'A'}]}
        point={'text':'test','fact_ids':['f']}
        self.review={'as_of':'2026-10-19','assets':[{'id':'A','candidate_thesis':point,'key_disagreement':point,
            'lenses':[{'id':k,'finding':'test','fact_ids':['f'],'missing_evidence':[]} for k in s.LENSES],
            'critique':[{'claim_under_review':'test','issue':'test','fact_ids':['f'],'revision':'test'}],
            'price_assessment':{'status':'insufficient_inputs','missing_inputs':['price']},
            'next_experiment':{'deliverable':'a','metric':'b','failure_condition':'c'}}]}

    def test_valid_review(self): s.validate_review(self.review,self.report)

    def test_fabricated_evidence_rejected(self):
        self.review['assets'][0]['lenses'][0]['fact_ids']=['invented']
        with self.assertRaises(ValueError): s.validate_review(self.review,self.report)

    def test_missing_lens_rejected(self):
        self.review['assets'][0]['lenses'].pop()
        with self.assertRaises(ValueError): s.validate_review(self.review,self.report)

    def test_unsupported_price_verdict_rejected(self):
        self.review['assets'][0]['price_assessment']['status']='cheap'
        with self.assertRaises(ValueError): s.validate_review(self.review,self.report)

    def test_gap_cannot_be_hidden(self):
        self.review['assets'][0]['lenses'][0]['fact_ids']=[]
        with self.assertRaises(ValueError): s.validate_review(self.review,self.report)

    def test_private_launcher_resolves_relative_output(self):
        report=dict(self.report,question='test',scope_limitations=[])
        assets=[{'id':'A','name':'A','kind':'equity','domains':['example.com'],'questions':['test']}]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            packet=Path(folder)/'packet.json'
            packet.write_text(json.dumps(report),encoding='utf-8')
            previous=Path.cwd()
            try:
                os.chdir(folder)
                with patch('sys.argv',['showcase.py','--private','--research-file',str(packet),'--output','relative']), patch.object(s.r,'load_watchlist',return_value=assets), patch.object(s.r,'validate_report'), patch.object(s.r,'invoke',return_value=(copy.deepcopy(self.review),{'search_events':0})), patch.object(s,'write_case') as write:
                    s.main()
                    self.assertTrue(write.call_args.args[3].is_absolute())
                    self.assertTrue(write.call_args.kwargs['private'])
            finally: os.chdir(previous)


if __name__=='__main__': unittest.main()
