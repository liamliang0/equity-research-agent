import copy,json,tempfile,unittest
from pathlib import Path
import company_models as m
import company_reports

ROOT=Path(__file__).parent

class ModelTests(unittest.TestCase):
    def earnings(self):return {'kind':'earnings','parameters':dict(eps=10,factor=1,pe=20,years=1,discount=.1),'reverse':dict(key='factor',range=[0,10])}
    def test_earnings_discount(self):self.assertAlmostEqual(m.evaluate(self.earnings())['value_per_share'],200/1.1)
    def test_reverse_roundtrip(self):
        model=self.earnings();price=m.evaluate(model,{'factor':1.7})['value_per_share']
        self.assertAlmostEqual(m.reverse(model,price),1.7)
    def test_unbracketed(self):self.assertIsNone(m.reverse(self.earnings(),1e6))
    def test_invalid_inputs(self):
        for change in ({'eps':float('nan')},{'pe':-1}):
            with self.assertRaises(ValueError):m.evaluate(self.earnings(),change)
    def test_dilution_reduces_equity_price(self):
        model={'kind':'growth_profit','parameters':dict(revenue=1000,growth=.1,margin=.2,shares=10,dilution=1,pe=20,discount=.1,years=3)}
        self.assertAlmostEqual(m.evaluate(model,{'dilution':2})['value_per_share'],m.evaluate(model)['value_per_share']/2)
    def test_reserve_assets_are_not_added_to_equity(self):
        model={'kind':'circle','parameters':dict(reserve_income=100,other_income=0,opex=70,balance_growth=0,yield_factor=1,retention=.5,other_growth=0,opex_growth=0,years=3,shares=10,dilution=1,tax=.2,pe=20,discount=.1)}
        self.assertEqual(m.evaluate(model)['value_per_share'],0)
        self.assertGreater(m.evaluate(model,{'retention':.9})['value_per_share'],0)
    def test_adr_ratio_direction(self):
        model={'kind':'adr','parameters':dict(local_price=1000000,fx=1250,ordinary_per_ads=.1,premium=.2)}
        self.assertEqual(m.evaluate(model)['value_per_share'],96)
    def test_public_cases_have_six_views_and_consistent_baselines(self):
        config=json.loads((ROOT/'examples/memory-company-profiles.json').read_text(encoding='utf-8'))
        self.assertEqual({p['symbol'] for p in config['profiles']},{'MU','SNDK'})
        for p in config['profiles']:
            self.assertEqual(len(p['views']),6)
            self.assertEqual(m.evaluate(p['model']),m.evaluate(p['model'],p['model']['scenarios']['base']))
            self.assertTrue(p['sources'][0]['receipt']['sha256'])
    def test_html_json_roundtrip(self):
        text='</script><script>bad</script> & test'
        payload=company_reports.json_script({'text':text})
        self.assertNotIn('</script>',payload)
        self.assertEqual(json.loads(payload)['text'],text)

if __name__=='__main__':unittest.main()
