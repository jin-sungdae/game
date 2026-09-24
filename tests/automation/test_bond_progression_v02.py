import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bond_v02', ROOT/'scripts/analysis/bond_progression_v02.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
class BondProgressionV02Test(unittest.TestCase):
    def test_deterministic_current_contract_and_separated_axes(self):
        data=a.analysis()
        self.assertEqual(data,a.analysis())
        self.assertEqual((data['bond5_minutes'],data['bond12_minutes']),(20,55))
        scenarios=list(data['scenarios_at_100_minutes'].values())
        self.assertEqual((scenarios[0]['level'],scenarios[0]['bond'],scenarios[0]['stage']),(8,0,1))
        self.assertEqual((scenarios[1]['level'],scenarios[1]['bond'],scenarios[1]['stage']),(1,21,1))
        self.assertEqual(scenarios[2]['evolution_minute'],{'MOKORI':20,'NEBLA':55})
        for s in scenarios[3:]:self.assertEqual(s['evolution_minute'],{'MOKORI':10,'NEBLA':50})
        self.assertEqual(scenarios[3]['berries_used'],12)
        self.assertEqual(scenarios[4]['berries_used'],2)
    def test_cooldown_boundary_and_berry_cost(self):
        self.assertEqual(a.scenario(False,True,False,299)['bond'],1)
        self.assertEqual(a.scenario(False,True,False,300)['bond'],2)
        berry=a.scenario(True,False,True,600)
        self.assertEqual((berry['stage'],berry['bond'],berry['gold']),(2,5,0))
