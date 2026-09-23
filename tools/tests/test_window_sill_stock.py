import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from measurement_quantities import geometry_digest
from window_sill_stock_review import calculate,from_folder


def window(identity,width,components=1):
    return {'opening_id':identity,'rough_opening_width_in':width,'assembly_quantity':1,'component_count':components}


class WindowSillTests(unittest.TestCase):
    def test_grouped_windows_make_one_sill_and_stock_respects_saw_kerf(self):
        result=calculate([window('triple',108,3)],{'sku':'12FT','length_inches':144})
        self.assertEqual(result['sill_members'],1);self.assertEqual(result['net_sill_lf'],9)
        self.assertEqual(result['candidate_whole_sticks'],1)
        result=calculate([window('a',72),window('b',72)],{'sku':'12FT','length_inches':144})
        self.assertEqual(result['candidate_whole_sticks'],2)
        exact=calculate([window('a',144)],{'sku':'12FT','length_inches':144})
        self.assertEqual(exact['boards'][0]['remaining_inches'],0)

    def test_fractional_width_rounds_up_and_every_piece_is_present_once(self):
        result=calculate([window('a',31.01),window('b',30),window('c',36)],{'sku':'12FT','length_inches':144})
        self.assertEqual(result['pieces'][0]['cut_inches'],31.125)
        self.assertEqual(result['candidate_whole_sticks'],1)
        self.assertEqual(sorted(c['piece_id'] for b in result['boards'] for c in b['cuts']),['sill:a','sill:b','sill:c'])
        self.assertAlmostEqual(result['boards'][0]['remaining_inches'],144-97.125-.375)

    def test_invalid_width_duplicate_assembly_and_oversized_unspliced_member_rejected(self):
        for entries in ([],[window('a',0)],[window('a',float('nan'))],[window('a',145)],
                        [window('a',30),window('a',40)],[{**window('a',30),'assembly_quantity':True}]):
            with self.subTest(entries=entries),self.assertRaises(ValueError):calculate(entries,{'sku':'12FT','length_inches':144})

    def test_sources_geometry_and_supplier_only_opening_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);supplier=b'Synthetic selected specification'
            (folder/'supplier.pdf').write_bytes(supplier)
            schedule={'plan_sha256':'plan','supplier_specification_sha256':hashlib.sha256(supplier).hexdigest(),
                'assemblies':[window('EO01',72),window('EG01',36)]}
            (folder/'schedule.json').write_text(json.dumps(schedule))
            state={'plan_sha256':'plan','version':3,'measurements':{'EO01':{'id':'EO01','kind':'length',
                'page':5,'points_per_foot':12,'points':[[0,0],[72,0]]}}}
            original=copy.deepcopy(state)
            config={'plan_sha256':'plan','schedule':{'path':'schedule.json','sha256':hashlib.sha256((folder/'schedule.json').read_bytes()).hexdigest()},
                'supplier':{'path':'supplier.pdf','sha256':schedule['supplier_specification_sha256']},
                'geometry_sha256':{'EO01':geometry_digest(state['measurements']['EO01'])},'supplier_only_openings':['EG01'],
                'stock':{'sku':'12FT','length_inches':144},'basis':'Test allowance','remaining':['Review assembly']}
            path=folder/'window_sill_stock_review.json';path.write_text(json.dumps(config))
            with patch('window_sill_stock_review.MeasurementStore') as store:
                store.return_value.read.side_effect=lambda:copy.deepcopy(state)
                current=from_folder(folder)
                self.assertEqual(current['supplier_only_openings'],['EG01'])
                self.assertEqual(current['sill_members'],2)
                self.assertFalse(current['purchase_order_released'])
                state['measurements']['EO01']['points'][1][0]+=12
                changed=from_folder(folder)
                self.assertEqual(changed['boards'],[]);self.assertIsNone(changed['sill_members'])
                self.assertEqual(changed['changed_measurements'],['EO01'])
                state=original;self.assertEqual(from_folder(folder),current)
                (folder/'supplier.pdf').write_bytes(b'Changed supplier')
                with self.assertRaisesRegex(ValueError,'source changed'):from_folder(folder)
                (folder/'supplier.pdf').write_bytes(supplier)
                config['supplier_only_openings']=[];path.write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError,'Every window'):from_folder(folder)

    def test_linked_gable_width_withholds_stale_stock_and_checks_source_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'main';gable=Path(temp)/'gable';folder.mkdir();gable.mkdir()
            supplier=b'Synthetic specification';(folder/'supplier.pdf').write_bytes(supplier)
            schedule={'plan_sha256':'plan','supplier_specification_sha256':hashlib.sha256(supplier).hexdigest(),
                'assemblies':[window('EO01',72),window('EG01',36)]}
            (folder/'schedule.json').write_text(json.dumps(schedule))
            (gable/'measurements.json').write_text('Synthetic configuration')
            measurement=lambda identity,width:{'id':identity,'kind':'length','page':9,
                'points_per_foot':12,'points':[[0,0],[width,0]]}
            state={'plan_sha256':'plan','version':3,'measurements':{'EO01':measurement('EO01',72)}}
            linked={'plan_sha256':'plan','version':1,'measurements':{'gable-width':measurement('gable-width',36),
                'gable-height':measurement('gable-height',60)}}
            config={'plan_sha256':'plan',
                'schedule':{'path':'schedule.json','sha256':hashlib.sha256((folder/'schedule.json').read_bytes()).hexdigest()},
                'supplier':{'path':'supplier.pdf','sha256':schedule['supplier_specification_sha256']},
                'geometry_sha256':{'EO01':geometry_digest(state['measurements']['EO01'])},
                'supplier_only_openings':[], 'stock':{'sku':'12FT','length_inches':144},
                'basis':'Test allowance','remaining':['Assembly needs review'],
                'linked_measurements':[{'job':'../gable',
                    'config_sha256':hashlib.sha256((gable/'measurements.json').read_bytes()).hexdigest(),
                    'openings':{'EG01':{'measurement_id':'gable-width',
                        'geometry_sha256':geometry_digest(linked['measurements']['gable-width']),
                        'related_geometry_sha256':{'gable-height':geometry_digest(linked['measurements']['gable-height'])}}}}]}
            path=folder/'window_sill_stock_review.json';path.write_text(json.dumps(config))
            def store(directory):
                current=state if Path(directory)==folder else linked
                return SimpleNamespace(folder=Path(directory),read=lambda:copy.deepcopy(current))
            with patch('window_sill_stock_review.MeasurementStore',side_effect=store):
                result=from_folder(folder)
                self.assertEqual(result['sill_members'],2)
                self.assertEqual(result['supplier_only_openings'],[])
                self.assertEqual(result['linked_measurement_versions'],[{'job':str(gable),'version':1}])
                linked['measurements']['gable-width']['points'][1][0]=42;linked['version']=2
                changed=from_folder(folder)
                self.assertEqual(changed['changed_measurements'],['EG01'])
                self.assertEqual(changed['boards'],[]);self.assertIsNone(changed['candidate_whole_sticks'])
                linked['measurements']['gable-width']['points'][1][0]=36;linked['version']=3
                self.assertEqual(from_folder(folder)['sill_members'],2)
                linked['measurements']['gable-height']['points'][1][0]=66
                self.assertEqual(from_folder(folder)['changed_measurements'],['EG01'])
                linked['measurements']['gable-height']['points'][1][0]=60
                linked['plan_sha256']='another-plan'
                with self.assertRaisesRegex(ValueError,'another drawing'):from_folder(folder)
                linked['plan_sha256']='plan'
                original=(gable/'measurements.json').read_bytes()
                (gable/'measurements.json').write_bytes(original+b'changed')
                with self.assertRaisesRegex(ValueError,'configuration changed'):from_folder(folder)
                (gable/'measurements.json').write_bytes(original)
                config['supplier_only_openings']=['EG01'];path.write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError,'duplicate source ownership'):from_folder(folder)
                config['supplier_only_openings']=[];config['linked_measurements'][0]['job']='.'
                path.write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError,'neighboring jobs'):from_folder(folder)


if __name__=='__main__':unittest.main()
