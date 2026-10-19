"""Rebuild the dated case from new APIs without claiming fresh AI-authored analysis."""
import argparse
from pathlib import Path
import market_data
import research_agent
import case_research
import report_ui
import utilities as u

if __name__=='__main__':
    root=Path(__file__).parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--watchlist',type=Path,default=root/'watchlist.case.example.json')
    p.add_argument('--profile',type=Path,default=root/'examples/avgo-case-profile.json')
    p.add_argument('--output',type=Path,default=root/'output/public-case')
    a=p.parse_args()
    a.output=a.output.resolve()
    snapshot=market_data.collect(research_agent.load_watchlist(a.watchlist),a.output/'data')
    profile=u.load(a.profile)
    case=case_research.build(snapshot,a.output/'data',profile['symbol'],profile)
    report_ui.render({'data_snapshot':snapshot},{'assets':[]},{'mode':'data-and-model-refresh','fresh_ai_analysis':False,'generated_at':u.now()},a.output,case)
    print(a.output/'index.html')
