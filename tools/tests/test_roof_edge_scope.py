import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from roof_edge_scope import from_folder,linked_folder


class RoofEdges(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.job=self.root/'draft';self.edges=self.root/'edges'
        self.sha=hashlib.sha256(b'fixed plan').hexdigest()
        common={'page':1,'points_per_foot':10,'width_pt':300,'height_pt':300,'dependent_rows':[]}
        self.face={**common,'id':'face','kind':'area','points':[[10,10],[110,10],[110,110],[10,110]]}
        edge={**common,'id':'rake','label':'Rake','kind':'length','edge_role':'rake',
              'points':[[10,10],[110,10]],'plane_gradients':[[.5,0]]}
        for folder,m in ((self.job,self.face),(self.edges,edge)):
            folder.mkdir();(folder/'plan.pdf').write_bytes(b'fixed plan')
            (folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[m]}))
        self.parent=MeasurementStore(self.job);self.store=MeasurementStore(self.edges)
        self.config={'plan_sha256':self.sha,'job':'../edges','config_sha256':self.store.read()['config_sha256'],
            'roof_measurements':{'face':geometry_digest(self.face)},'basis':'Reviewed source edges'}
        self.path=self.job/'roof_edge_review.json';self.path.write_text(json.dumps(self.config))

    def test_saved_edge_edit_updates_length_without_a_purchase_quantity(self):
        before=from_folder(self.job,self.sha,1);item=before['items'][0]
        self.assertAlmostEqual(item['reference_quantity'],10*(1.25**.5));self.assertIsNone(item['purchase_quantity'])
        self.store.save('rake',[[10,10],[120,10]],1,self.sha,'test extension')
        after=from_folder(self.job,self.sha,1)
        self.assertEqual(after['edge_measurement_version'],2)
        self.assertAlmostEqual(after['items'][0]['reference_quantity'],11*(1.25**.5))
        self.assertFalse(after['complete_accessory_scope'])

    def test_changed_roof_face_requires_reconciliation(self):
        self.parent.save('face',[[10,10],[120,10],[120,110],[10,110]],1,self.sha,'roof revision')
        with self.assertRaisesRegex(ValueError,'Roof faces changed'):from_folder(self.job,self.sha,2)

    def test_other_plan_config_or_outside_job_is_rejected(self):
        for update in ({'plan_sha256':'other'},{'config_sha256':'changed'},{'job':'../../elsewhere'}):
            self.path.write_text(json.dumps({**self.config,**update}))
            with self.subTest(update=update),self.assertRaises(ValueError):from_folder(self.job,self.sha,1)
        with self.assertRaises(ValueError):linked_folder(self.job,{'job':'.'})


if __name__=='__main__':unittest.main()
