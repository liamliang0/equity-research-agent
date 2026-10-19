import unittest
import math
import json
from pathlib import Path
import case_research as c


class PeriodTests(unittest.TestCase):
    def rows(self):
        return [{'start':'2024-01-01','end':'2024-12-31','val':100,'filed':'2025-02-01'},
                {'start':'2024-01-01','end':'2024-09-30','val':70,'filed':'2025-10-01'},
                {'start':'2025-01-01','end':'2025-09-30','val':90,'filed':'2025-10-01'}]

    def test_ttm_is_not_ytd_annualization(self):
        self.assertEqual(c.ttm(self.rows(),'2025-09-30')['value'],120)

    def test_missing_comparable_fails(self):
        with self.assertRaises(ValueError): c.ttm([self.rows()[0],self.rows()[2]],'2025-09-30')

    def test_quarter_derived_from_cumulative(self):
        rows=[{'start':'2025-01-01','end':'2025-06-30','val':50,'filed':'2025-08-01'},
              {'start':'2025-01-01','end':'2025-09-30','val':90,'filed':'2025-11-01'}]
        self.assertEqual(c.last_quarter(rows,'2025-09-30')['value'],40)

    def test_stale_direct_quarter_not_used(self):
        rows=[{'start':'2025-01-01','end':'2025-03-31','val':20,'filed':'2025-05-01'},
              {'start':'2025-01-01','end':'2025-09-30','val':90,'filed':'2025-11-01'}]
        with self.assertRaises(ValueError): c.last_quarter(rows,'2025-09-30')


class CaseValuationTests(unittest.TestCase):
    def test_flat_cash_perpetuity(self):
        self.assertAlmostEqual(c.cash_dcf(100,100,10,0,.1,0)['value_per_share'],90)

    def test_reverse_round_trip(self):
        price=c.cash_dcf(100,50,10,.25,.11,.03)['value_per_share']
        self.assertAlmostEqual(c.reverse_growth(100,50,10,price,.11,.03),.25,places=9)

    def test_no_root_does_not_fabricate(self):
        self.assertIsNone(c.reverse_growth(100,50,10,1e20,.11,.03))

    def test_invalid_spread_rejected(self):
        with self.assertRaises(ValueError): c.cash_dcf(100,50,10,.25,.03,.03)

    def test_higher_discount_lowers_value(self):
        self.assertGreater(c.cash_dcf(100,50,10,.25,.10,.03)['value_per_share'],c.cash_dcf(100,50,10,.25,.12,.03)['value_per_share'])

    def test_actual_case_reconciles_rounded_announcement(self):
        case=json.loads((Path(__file__).parent/'examples/complete-case.json').read_text(encoding='utf-8'))
        self.assertLess(abs(case['quarters']['cfo']['value']/1e9-14.2),.05)
        self.assertLess(abs((case['quarters']['cfo']['value']-case['quarters']['capex']['value'])/1e9-13.7),.05)
        for value in case['ttm'].values():
            self.assertEqual(value['end'],case['financial_period']['end'])
            if len(value['inputs'])==3:
                a,b,p=value['inputs']
                self.assertEqual(a['val']+b['val']-p['val'],value['value'])


if __name__=='__main__': unittest.main()


class ReportSafetyTests(unittest.TestCase):
    def test_embedded_json_preserves_text_without_script_breakout(self):
        import tempfile
        import report_ui
        root=Path(__file__).parent
        case=json.loads((root/'examples/complete-case.json').read_text(encoding='utf-8'))
        snapshot=json.loads((root/'examples/complete-case-data.json').read_text(encoding='utf-8'))
        case['profile']['thesis']='</script><script>alert(1)</script> & test'
        with tempfile.TemporaryDirectory(dir=root) as folder:
            report_ui.render({'data_snapshot':snapshot},{'assets':[]},{},folder,case)
            page=(Path(folder)/'index.html').read_text(encoding='utf-8')
            payload=page.split('<script id="case-data" type="application/json">',1)[1].split('</script>',1)[0]
            self.assertNotIn('</script>',payload)
            self.assertEqual(json.loads(payload)['profile']['thesis'],case['profile']['thesis'])
