import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_stud_layout import layout, main


def fixture():
    runs = [{'id':'W1','orientation':'horizontal','coordinate_pt':20,
             'start_pt':0,'end_pt':96,'source':'synthetic measured wall'}]
    zones = [{'assembly':name,'run':'W1','interval':span,'source':'synthetic assembly'}
             for name, span in [('start',[-4,4]),('door',[30,52]),('end',[92,100])]]
    return runs, zones


class FieldStudLayout(unittest.TestCase):
    def test_cli_uses_company_default_and_preserves_project_override(self):
        import json
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);runs,zones=fixture()
            inputs={'runs':runs,'zones':zones,'points_per_foot':12,'first_center_inches':.75}
            (root/'input.json').write_text(json.dumps(inputs),encoding='utf-8')
            args=['--input',str(root/'input.json'),'--output',str(root/'output.json')]
            with redirect_stdout(StringIO()):main(args)
            output=json.loads((root/'output.json').read_text(encoding='utf-8'))
            self.assertEqual(output['spacing_inches'],16)
            self.assertEqual(output['spacing_provenance']['basis'],'company_default')
            with self.assertRaises(FileExistsError):main(args)
            inputs['project_overrides']={'framing.stud_spacing_inches':24}
            (root/'input.json').write_text(json.dumps(inputs),encoding='utf-8')
            args[-1]=str(root/'override.json')
            with redirect_stdout(StringIO()):main(args)
            override=json.loads((root/'override.json').read_text(encoding='utf-8'))
            self.assertEqual(override['spacing_inches'],24)
            self.assertEqual(override['spacing_provenance']['basis'],'project_override')
            self.assertEqual(len(override['profile_conflicts']),1)

    def calculate(self, runs, zones, **options):
        return layout(runs,zones,**{'points_per_foot':12,'spacing_inches':16,
                                  'first_center_inches':.75,**options})

    def test_enumerates_field_and_reserved_stations(self):
        result=self.calculate(*fixture())
        self.assertEqual([s['along_pt'] for s in result['field_studs']],[16.75,64.75,80.75])
        self.assertEqual(result['reserved_count'],3)
        self.assertIsNone(result['purchase_quantity'])

    def test_overlapping_reservations_do_not_double_deduct(self):
        runs,zones=fixture();zones.append(dict(zones[1],assembly='backing'))
        result=self.calculate(runs,zones)
        self.assertEqual(result['field_count'],3)
        self.assertEqual(result['reserved_stations'][1]['assembly_owners'],['backing','door'])

    def test_translation_scale_and_axis_preserve_quantities(self):
        runs,zones=fixture();original=self.calculate(runs,zones)
        runs[0].update(start_pt=100,end_pt=292,coordinate_pt=70,orientation='vertical')
        for z in zones:z['interval']=[100+2*x for x in z['interval']]
        changed=self.calculate(runs,zones,points_per_foot=24)
        self.assertEqual(changed['field_count'],original['field_count'])
        self.assertEqual(changed['field_studs'][0]['point_pt'],[70,133.5])

    def test_changed_opening_and_datum_recalculate(self):
        runs,zones=fixture();zones[1]['interval']=[14,52]
        self.assertEqual(self.calculate(runs,zones)['field_count'],2)
        self.assertEqual(self.calculate(*fixture(),first_center_inches=8)['field_count'],5)

    def test_missing_or_stale_end_reservations_refuse_count(self):
        runs,zones=fixture()
        with self.assertRaises(ValueError):self.calculate(runs,zones[:-1])
        runs[0]['end_pt']=120
        with self.assertRaises(ValueError):self.calculate(runs,zones)

    def test_invalid_numbers_sources_and_duplicate_runs_refused(self):
        for value in (True,0,-1,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.calculate(*fixture(),points_per_foot=value)
        runs,zones=fixture()
        with self.assertRaises(ValueError):self.calculate(runs+runs,zones)
        for mutation in ({'source':''},{'orientation':'diagonal'},{'start_pt':96}):
            changed=copy.deepcopy(runs);changed[0].update(mutation)
            with self.assertRaises(ValueError):self.calculate(changed,zones)
        for mutation in ({'run':'missing'},{'source':''},{'interval':[200,210]}):
            changed=copy.deepcopy(zones);changed[1].update(mutation)
            with self.assertRaises(ValueError):self.calculate(runs,changed)


if __name__=='__main__':unittest.main()
