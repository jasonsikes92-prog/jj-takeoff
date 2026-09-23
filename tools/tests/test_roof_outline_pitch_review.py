import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import fitz
from roof_face_candidates import candidates
from roof_outline_pitch_review import candidate_sha256, read_review, reviewed_candidates
from measurement_store import calculate


class RoofOutlinePitchReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.job = Path(self.temp.name)
        doc = fitz.open()
        page = doc.new_page(width=400, height=400)
        page.draw_rect(fitz.Rect(20, 20, 200, 200), color=(1, 0, 0), width=2)
        doc.new_page(width=400, height=400).insert_text((40, 50), '6 : 12')
        doc.save(self.job/'plan.pdf')
        doc.close()
        self.sha = hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        with fitz.open(self.job/'plan.pdf') as doc:
            self.raw = candidates(doc[0], 18, [10, 10, 220, 220], [{'color':[1, 0, 0], 'width_pt':2}])
            line = doc[1].get_text('dict')['blocks'][0]['lines'][0]
        self.review = {'plan_sha256':self.sha, 'reviewer':'Test reviewer', 'basis':'Source association fixture',
            'outlines':[{'source_outline_sha256':self.raw['unresolved_source_outlines'][0]['source_sha256'],
                'basis':'Reviewed front elevation corresponds to the unlabeled roof face.',
                'pitch_label':{'page':2, 'text':'6 : 12', 'bbox_pt':list(line['bbox'])}}]}
        self.frame = {'page':1, 'points_per_foot':18, 'width_pt':400, 'height_pt':400}
        self.save()

    def save(self):
        (self.job/'roof_outline_pitch_review.json').write_text(json.dumps(self.review))

    def resolve(self, raw=None, review=None, frame=None):
        return reviewed_candidates(self.job/'plan.pdf', self.raw if raw is None else raw,
            read_review(self.job, self.sha) if review is None else review, self.frame if frame is None else frame)

    def test_cross_sheet_label_adds_source_bound_area_without_certifying_pitch(self):
        measurement = self.resolve()[0]
        self.assertAlmostEqual(calculate(measurement)['quantity'], 100*math.hypot(12, 6)/12)
        self.assertEqual(measurement['source_pitch_evidence']['label']['page'], 2)
        self.assertTrue(measurement['source_pitch_evidence']['pitch_is_inferred'])
        self.assertFalse(measurement['source_pitch_evidence']['pitch_certified'])
        self.assertFalse(measurement['source_pitch_review']['reviewer_identity_authenticated'])
        self.assertEqual(measurement['points'], self.raw['unresolved_source_outlines'][0]['points'])

    def test_changed_label_location_text_page_or_repeated_outline_is_rejected(self):
        for key, value in [('text','8 : 12'), ('page',1), ('page',True), ('bbox_pt',[0,0,10,10])]:
            changed = copy.deepcopy(read_review(self.job, self.sha))
            changed['outlines'][0]['pitch_label'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.resolve(review=changed)
        changed = read_review(self.job, self.sha)
        changed['outlines'] *= 2
        with self.assertRaisesRegex(ValueError, 'repeated'):
            self.resolve(review=changed)

    def test_conflicting_unreviewed_and_stale_geometry_cannot_be_overridden(self):
        for key, value in [('pitch_labels',[{'rise':4}]), ('source_style_reviewed',False), ('source_sha256','stale')]:
            changed = copy.deepcopy(self.raw)
            changed['unresolved_source_outlines'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.resolve(raw=changed)

    def test_review_requires_current_plan_reviewer_basis_and_scale(self):
        for key, value in [('plan_sha256','old'), ('reviewer',''), ('basis',''), ('outlines',[])]:
            original = self.review[key]
            self.review[key] = value
            self.save()
            with self.subTest(key=key), self.assertRaises(ValueError):
                read_review(self.job, self.sha)
            self.review[key] = original
        self.save()
        with self.assertRaisesRegex(ValueError, 'calibrated'):
            reviewed_candidates(self.job/'plan.pdf', self.raw, read_review(self.job,self.sha), None)
        with (self.job/'plan.pdf').open('ab') as f:
            f.write(b'\n')
        with self.assertRaisesRegex(ValueError, 'drawing changed'):
            self.resolve()

    def test_overprinted_identical_source_label_is_one_anchor(self):
        with fitz.open(self.job/'plan.pdf') as doc:
            doc[1].insert_text((40, 50), '6 : 12')
            raw = doc.tobytes()
        (self.job/'plan.pdf').write_bytes(raw)
        self.sha = hashlib.sha256(raw).hexdigest()
        self.review['plan_sha256'] = self.sha
        self.save()
        self.assertEqual(len(self.resolve()), 1)

    def prepare_conflicting_outline(self):
        self.raw['unresolved_source_outlines'][0]['pitch_labels']=[{'rise':6},{'rise':4}]
        candidate={'id':'subdivision','page':1,'points':[[40,40],[100,40],[100,100],[40,100]],
            'points_per_foot':18,'surface_factor':math.hypot(12,6)/12,'source_cad_paths':[0],
            'pitch_candidate':{'rise':6,'text':'6 : 12'}}
        self.raw['measurements']=[candidate]
        item=self.review['outlines'][0]
        item['conflicting_label_basis']='The 4:12 canopy is below this 6:12 main roof.'
        item['superseded_measurements']=[{'measurement_id':candidate['id'],
            'source_candidate_sha256':candidate_sha256(candidate)}]
        self.save()
        return candidate

    def test_reviewed_conflict_retains_explicit_same_pitch_replacement_evidence(self):
        self.prepare_conflicting_outline()
        measurement=self.resolve()[0]
        self.assertEqual(measurement['source_pitch_evidence']['superseded_measurements'],
            self.review['outlines'][0]['superseded_measurements'])
        self.assertIn('canopy',measurement['source_pitch_evidence']['conflicting_label_basis'])
        self.assertFalse(measurement['source_pitch_evidence']['pitch_certified'])

    def test_conflict_replacement_rejects_changed_missing_duplicate_or_unrelated_candidate(self):
        self.prepare_conflicting_outline()
        for change in ('stale','missing','duplicate','different_pitch','outside'):
            raw=copy.deepcopy(self.raw);review=read_review(self.job,self.sha)
            replacement=review['outlines'][0]['superseded_measurements'][0]
            if change=='stale':raw['measurements'][0]['points'][0][0]+=1
            if change=='missing':raw['measurements']=[]
            if change=='duplicate':review['outlines'][0]['superseded_measurements']*=2
            if change=='different_pitch':raw['measurements'][0]['pitch_candidate']['rise']=4
            if change=='outside':raw['measurements'][0]['points']=[[250,250],[300,250],[300,300],[250,300]]
            if change in ('different_pitch','outside'):
                replacement['source_candidate_sha256']=candidate_sha256(raw['measurements'][0])
            with self.subTest(change=change),self.assertRaises(ValueError):self.resolve(raw=raw,review=review)

    def test_conflicting_label_review_cannot_omit_replacement_or_explanation(self):
        self.prepare_conflicting_outline()
        for field in ('superseded_measurements','conflicting_label_basis'):
            review=read_review(self.job,self.sha);del review['outlines'][0][field]
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'partition review'):
                self.resolve(review=review)


if __name__ == '__main__':
    unittest.main()
