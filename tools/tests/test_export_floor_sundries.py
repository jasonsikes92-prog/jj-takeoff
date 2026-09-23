import json
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import box,mapping
import test_floor_sundries as fixtures
from export_floor_sundries import export


class ExportFloorSundriesTests(unittest.TestCase):
    def test_two_room_export_preserves_sources_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'input.json';out=root/'output.json'
            source={'coordinate_unit':'feet','plan_sha256':'test-plan','measurement_version':1,
                'products':fixtures.FloorSundriesTests().products(),
                'fields':[{'id':identity,'measurement_ids':[identity],'basis':'Separate synthetic installation field',
                           'geometry_ft':mapping(box(0,0,5,6))} for identity in ('bath-a','bath-b')]}
            path.write_text(json.dumps(source));result=export(path,out)
            self.assertEqual(json.loads(out.read_bytes()),json.loads(json.dumps(result)))
            self.assertEqual(result['installed_area_sf'],60)
            self.assertFalse(result['published_to_estimate']);self.assertFalse(result['order_released'])
            before=out.read_bytes()
            with self.assertRaises(FileExistsError):export(path,out)
            self.assertEqual(out.read_bytes(),before)
            source['coordinate_unit']='points';path.write_text(json.dumps(source))
            with self.assertRaises(ValueError):export(path,root/'bad.json')
            self.assertFalse((root/'bad.json').exists())


if __name__=='__main__':unittest.main()
