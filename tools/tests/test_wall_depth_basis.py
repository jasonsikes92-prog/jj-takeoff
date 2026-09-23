import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_profile import initialize
from wall_depth_basis import read_wall_depth_basis


class WallDepthBasis(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=self.root/'source.pdf'
        with fitz.open() as doc:doc.new_page();doc.save(self.plan)
        self.digest=hashlib.sha256(self.plan.read_bytes()).hexdigest()
        self.profile=self.root/'profile.json'
        self.profile.write_text(json.dumps({'profile_id':'test','version':1,'rules':[
            {'key':'framing.stud_size','value':'2x4','source':'Owner test rule','when':{}}]}))

    def job(self,name,overrides=None):
        job=self.root/name;initialize(self.plan,job,self.profile,project_overrides=overrides)
        return job

    def test_default_and_project_override_keep_separate_provenance(self):
        original=self.profile.read_bytes()
        default=read_wall_depth_basis(self.job('default'),self.digest)
        revised=read_wall_depth_basis(self.job('override',{'framing.stud_size':'2x6'}),self.digest)
        self.assertEqual((default['depth_inches'],revised['depth_inches']),(3.5,5.5))
        self.assertEqual(default['provenance']['basis'],'company_default')
        self.assertEqual(revised['provenance']['basis'],'project_override')
        self.assertFalse(default['drawing_verified']);self.assertEqual(self.profile.read_bytes(),original)

    def test_no_intake_and_unsupported_size_do_not_guess(self):
        self.assertIsNone(read_wall_depth_basis(self.root/'absent',self.digest))
        result=read_wall_depth_basis(self.job('large',{'framing.stud_size':'2x8'}),self.digest)
        self.assertIsNone(result['depth_inches']);self.assertEqual(result['nominal_stud_size'],'2x8')

    def test_changed_setting_and_foreign_plan_rejected(self):
        job=self.job('altered')
        with self.assertRaisesRegex(ValueError,'another drawing'):read_wall_depth_basis(job,'different')
        path=job/'estimate_intake.json';value=json.loads(path.read_bytes())
        value['settings']['framing.stud_size']='2x6';path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'differs from its resolved'):read_wall_depth_basis(job,self.digest)

    def test_changed_or_external_snapshot_rejected(self):
        job=self.job('snapshot');path=job/'estimate_intake.json';value=json.loads(path.read_bytes())
        (job/value['company_profile_snapshot']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'snapshot changed'):read_wall_depth_basis(job,self.digest)
        value['company_profile_snapshot']='../profile.json';path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'inside the job'):read_wall_depth_basis(job,self.digest)


if __name__=='__main__':unittest.main()
