import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jnj_takeoff import _classify_cab

class CabinetTags(unittest.TestCase):
    def test_drawer_and_oven_bases_on_roberts_elevations(self):
        for tag,width in [('3DB12',12),('3DB36',36),('2DB18',18),('OB33',33)]:
            self.assertEqual(_classify_cab(tag),('lower',width))
    def test_towers_use_actual_printed_width(self):
        for tag,width in [('U242496L',24),('U302496R',30),('U362496',36),('OTC33',33)]:
            self.assertEqual(_classify_cab(tag),('tall',width))
    def test_corner_wall_and_ordinary_base(self):
        self.assertEqual(_classify_cab('DCW2442R'),('upper',24))
        self.assertEqual(_classify_cab('DCB36R'),('lower',36))
        self.assertEqual(_classify_cab('B12R'),('lower',12))
    def test_appliance_and_filler_labels_are_not_cabinet_boxes(self):
        for tag in ['DW','VANITY','BF6','WF660']:
            self.assertIsNone(_classify_cab(tag))

if __name__=='__main__':unittest.main()
