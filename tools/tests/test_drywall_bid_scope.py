import copy
import unittest
from drywall_bid_scope import build_scope,render_markdown,estimating_practice,PRACTICE_KEYS
from company_profile import resolve


class DrywallBidScope(unittest.TestCase):
    def setUp(self):
        self.r={'id':'room','page':1,'room_use_confirmed':True,'room_use_review':{'name':'Bedroom'},
            'ceiling_reference':{'noted_height_inches':108,'status':'height_note_only'},
            'wall_surface_reference':{'status':'constant_height_geometric_reference','gross_wall_surface_sf':396},
            'ceiling_surface':{'status':'current_source_review','surface_area_sf':120}}
        self.rooms={'plan_sha256':'plan','measurement_version':1,'source_sha256':'source','regions':[self.r],
            'ceiling_surface_review':{'unreviewed_region_ids':[]}}

    def test_surface_units_are_separate_and_no_price_or_complete_quantity_is_invented(self):
        scope=build_scope(self.rooms);wall,ceiling=scope['items']
        self.assertEqual((wall['reference_quantity'],wall['reference_unit']),(396,'gross wall SF'))
        self.assertEqual((ceiling['reference_quantity'],ceiling['reference_unit']),(120,'ceiling surface SF'))
        self.assertTrue(all(i['unit_price'] is None and i['quoted_quantity'] is None for i in scope['items']))
        self.assertIsNone(scope['whole_house_drywall_quantity']);self.assertFalse(scope['sent'])
        self.assertFalse(scope['scope_coverage_certified']);self.assertFalse(scope['ready_to_order'])
        self.assertEqual(len(scope['scope_requirements']),8)

    def test_stale_values_are_withheld_and_unknowns_do_not_become_zero(self):
        self.r['wall_surface_reference']['status']='unresolved_wall_height_or_profile'
        self.r['ceiling_surface']['status']='stale_source_review'
        self.r['room_use_confirmed']=False
        scope=build_scope(self.rooms)
        self.assertTrue(all(i['reference_quantity'] is None and i['room_name'] is None for i in scope['items']))
        self.assertEqual(len(scope['unmeasured_surface_ids']),2)
        rendered=render_markdown(scope);self.assertIn('Not measured',rendered);self.assertNotIn('396',rendered)

    def test_current_revision_and_scope_changes_change_fingerprint(self):
        first=build_scope(self.rooms)
        self.rooms['measurement_version']=2
        self.assertNotEqual(first['scope_sha256'],build_scope(self.rooms)['scope_sha256'])
        self.rooms['measurement_version']=1;self.r['ceiling_surface']['surface_area_sf']=125
        self.assertNotEqual(first['scope_sha256'],build_scope(self.rooms)['scope_sha256'])

    def test_no_enclosed_rooms_is_missing_scope_not_zero_drywall(self):
        self.rooms['regions']=[];self.rooms['unresolved_gap_ids']=['gap1']
        scope=build_scope(self.rooms)
        self.assertTrue(scope['source_exceptions']['no_closed_room_regions'])
        self.assertIsNone(scope['whole_house_drywall_quantity'])
        self.assertFalse(scope['ready_to_order'])
        self.assertIn('empty schedule does not mean zero drywall',render_markdown(scope))
        self.assertIn('1 wall gaps require resolution',render_markdown(scope))

    def test_mixed_ceiling_parts_reach_bid_and_stale_parts_are_withheld(self):
        from ceiling_surface_review import apply,binding
        region={'id':'room','page':1,'points_per_foot':10,
            'points':[[0,0],[100,0],[100,100],[0,100]],'holes':[],
            'ceiling_notes':[],'ceiling_reference':{'status':'height_note_only'}}
        decision={'region_id':'room','source_sha256':binding('plan',region),
            'scope':'entire_region','surface_type':'partitioned','basis':'Reviewed ceiling transitions',
            'parts':[{'id':'hall','points':[[0,0],[40,0],[40,100],[0,100]],
                      'rise_per_12':0,'basis':'Flat hall'},
                     {'id':'living','points':[[40,0],[100,0],[100,100],[40,100]],
                      'rise_per_12':4,'basis':'Living vault'}]}
        reviewed=apply({'plan_sha256':'plan','source_sha256':'source','regions':[region]},
            {'plan_sha256':'plan','reviewer':'Test reviewer','decisions':[decision]})
        self.r['ceiling_surface']=reviewed['regions'][0]['ceiling_surface']
        scope=build_scope(self.rooms);ceiling=scope['items'][1]
        self.assertAlmostEqual(ceiling['reference_quantity'],sum(p['surface_area_sf'] for p in ceiling['ceiling_parts']))
        text=render_markdown(scope)
        self.assertIn('Mixed ceiling breakdown',text);self.assertIn('do not add them again',text)
        self.assertIn('Flat hall',text);self.assertIn('Living vault',text)
        self.r['ceiling_surface']['parts'][0]['basis']='Changed basis'
        self.assertNotEqual(scope['scope_sha256'],build_scope(self.rooms)['scope_sha256'])
        self.assertEqual(ceiling['ceiling_parts'][0]['basis'],'Flat hall')
        self.r['ceiling_surface']['status']='stale_source_review'
        stale=build_scope(self.rooms)
        self.assertNotIn('ceiling_parts',stale['items'][1])
        self.assertNotIn('Mixed ceiling breakdown',render_markdown(stale))

    def test_unique_rooms_and_source_revision_required(self):
        self.rooms['regions'].append(copy.deepcopy(self.r))
        with self.assertRaises(ValueError):build_scope(self.rooms)
        self.rooms['regions'].pop();self.rooms['measurement_version']=0
        with self.assertRaises(ValueError):build_scope(self.rooms)

    def test_render_preserves_scope_questions_and_escapes_room_text(self):
        self.r['room_use_review']['name']='Bedroom | west\nside'
        text=render_markdown(build_scope(self.rooms))
        self.assertIn('Bedroom \\| west side',text)
        self.assertIn('floor SF, actual wall-and-ceiling SF, sheets or a lump sum',text)
        self.assertIn('Missing quantities are unresolved, not zero',text)
        self.assertIn('Do not add package and component prices',text)

    def test_saved_practices_reach_request_without_repricing_gross_geometry(self):
        profile={'version':1,'rules':[{'key':key,'value':value,'source':'Owner answer'}
            for key,value in zip(PRACTICE_KEYS,[False,0])]}
        practice=estimating_practice(resolve(profile),{'intake_sha256':'frozen'})
        scope=build_scope(self.rooms,practice);text=render_markdown(scope)
        self.assertIn('Do not deduct windows or doors',text)
        self.assertIn('Added billing waste: 0%',text)
        self.assertIn('separate from material cutting waste',text)
        self.assertEqual(scope['items'],build_scope(self.rooms)['items'])
        self.assertFalse(practice['supplier_acceptance_confirmed'])
        self.assertIsNone(practice['material_purchase_waste_percent'])
        self.assertEqual(practice['unresolved_settings'],[])
        override=estimating_practice(resolve(profile,project_overrides=dict(zip(PRACTICE_KEYS,[True,5]))))
        changed=build_scope(self.rooms,override)
        self.assertNotEqual(scope['scope_sha256'],changed['scope_sha256'])
        self.assertEqual(scope['items'],changed['items'])
        self.assertEqual(override['provenance'][PRACTICE_KEYS[0]]['basis'],'project_override')
        self.assertIn('Deduct windows and doors',render_markdown(changed))
        self.assertIn('Added billing waste: 5%',render_markdown(changed))

    def test_missing_and_invalid_practices_do_not_become_zero(self):
        scope=build_scope(self.rooms)
        self.assertEqual(scope['estimating_practice']['unresolved_settings'],list(PRACTICE_KEYS))
        self.assertIn('not established for this job',render_markdown(scope))
        self.assertNotIn('Added billing waste: 0%',render_markdown(scope))
        for key,value in [(PRACTICE_KEYS[0],'false'),(PRACTICE_KEYS[0],0),
                (PRACTICE_KEYS[1],True),(PRACTICE_KEYS[1],-1),(PRACTICE_KEYS[1],float('nan'))]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                estimating_practice({'settings':{key:value},'provenance':{key:{'basis':'test'}}})


if __name__=='__main__':unittest.main()
