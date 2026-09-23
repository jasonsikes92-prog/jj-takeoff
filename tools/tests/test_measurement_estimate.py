import copy
import sys
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_estimate import template_draft, price_draft


class TemplateDraft(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.evidence=Path(self.tmp.name)
        (self.evidence/'quote.txt').write_bytes(b'Synthetic quote: $2.25 per SF')
        self.state={'version':1,'plan_sha256':'plan','measurements':{
            'floor':{'kind':'area','points':[[0,0],[100,0],[100,100],[0,100]],
                     'width_pt':500,'height_pt':500,'points_per_foot':10}}}
        self.rule={'id':'floor','label':'Floor','measurement_ids':['floor'],'unit':'SF',
                   'rounding':'whole_up','template_rows':['101'],'use':'template_quantity',
                   'basis':'Measured floor','remaining':['Current package price']}
        self.rules={'plan_sha256':'plan','rules':[self.rule]}
        self.template={'rows':[{'row_id':'template-101','excel_row':'101','name':'Engineered floor',
            'unit':'ft2','markup_pct':'15','cost_type':'MATERIAL','completion_status':'evidence_in_progress'}]}

    def test_edit_updates_quantity_preserving_template_and_unknown_price(self):
        original=copy.deepcopy(self.template)
        self.assertEqual(template_draft(self.state,self.rules,self.template)['rows'][0]['draft_quantity'],100)
        self.state['measurements']['floor']['points']=[[0,0],[200,0],[200,100],[0,100]]
        self.state['version']=2
        result=template_draft(self.state,self.rules,self.template)
        self.assertEqual(result['rows'][0]['draft_quantity'],200)
        self.assertEqual(result['rows'][0]['markup_pct'],'15')
        self.assertIsNone(result['rows'][0]['line_price'])
        self.assertIsNone(result['whole_house_total'])
        self.assertFalse(result['estimate_released'])
        self.assertEqual(self.template,original)

    def test_assembly_input_never_becomes_template_quantity(self):
        self.rule['use']='assembly_input'
        result=template_draft(self.state,self.rules,self.template)
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(len(result['rows'][0]['assembly_inputs']),1)

    def test_linear_feet_label_accepts_length_but_not_area(self):
        self.template['rows'][0]['unit']='feet'
        with self.assertRaisesRegex(ValueError,'unit does not match'):
            template_draft(self.state,self.rules,self.template)
        self.state['measurements']['floor'].update(kind='length',points=[[0,0],[75,0]])
        self.rule['unit']='LF'
        row=template_draft(self.state,self.rules,self.template)['rows'][0]
        self.assertEqual(row['unit'],'feet')
        self.assertEqual(row['draft_quantity'],8)
        self.assertIsNone(row['line_cost'])

    def test_conflicting_targets_or_units_are_rejected(self):
        for mode in ['missing','duplicate','unit','group','excluded']:
            with self.subTest(mode=mode):
                rules=copy.deepcopy(self.rules);template=copy.deepcopy(self.template)
                if mode=='missing':rules['rules'][0]['template_rows']=['999']
                if mode=='duplicate':rules['rules'].append({**copy.deepcopy(self.rule),'id':'second'})
                if mode=='unit':template['rows'][0]['unit']='each'
                if mode=='group':template['rows'][0]['cost_type']='GROUP'
                if mode=='excluded':template['rows'][0]['completion_status']='not_applicable_plan_baseline'
                with self.assertRaises(ValueError):template_draft(self.state,rules,template)

    def pricing(self):
        return {'plan_sha256':'plan','measurement_version':1,'rates':[{
            'row_id':'template-101','unit':'ft2','currency':'USD','unit_price':2.25,
            'date':'2026-09-16','valid_through':'2026-09-30','source':'Synthetic supplier quote',
            'source_file':'quote.txt','source_sha256':hashlib.sha256((self.evidence/'quote.txt').read_bytes()).hexdigest(),'evidence_kind':'current_supplier_quote',
            'scope_reviewed':True,'pricing_basis':'unit_rate'}]}

    def test_dated_rate_uses_preserved_markup_without_releasing_total(self):
        draft=template_draft(self.state,self.rules,self.template)
        result=price_draft(draft,self.pricing(),'2026-09-16',self.evidence)
        self.assertEqual(result['rows'][0]['line_cost'],225)
        self.assertEqual(result['rows'][0]['line_price'],258.75)
        self.assertIsNone(draft['rows'][0]['line_price'])
        self.assertIsNone(result['whole_house_total'])
        self.assertFalse(result['estimate_released'])

    def test_expired_or_wrong_unit_prices_stay_unpriced(self):
        draft=template_draft(self.state,self.rules,self.template)
        for change in ['expired','unit']:
            price=self.pricing()
            if change=='expired':price['rates'][0]['valid_through']='2026-09-16'
            else:price['rates'][0]['unit']='package'
            result=price_draft(draft,price,'2026-09-17',self.evidence)
            self.assertIsNone(result['rows'][0]['line_cost'])
            self.assertIsNone(result['rows'][0]['line_price'])

    def test_old_revision_historical_rates_and_packages_are_rejected(self):
        draft=template_draft(self.state,self.rules,self.template)
        for change in ['version','historical','package','duplicate']:
            price=self.pricing()
            if change=='version':price['measurement_version']=2
            if change=='historical':price['rates'][0]['evidence_kind']='historical_invoice'
            if change=='package':price['rates'][0]['pricing_basis']='package'
            if change=='duplicate':price['rates'].append(copy.deepcopy(price['rates'][0]))
            with self.assertRaises(ValueError):price_draft(draft,price,'2026-09-16',self.evidence)

    def test_changed_source_file_invalidates_price(self):
        draft=template_draft(self.state,self.rules,self.template);price=self.pricing()
        (self.evidence/'quote.txt').write_bytes(b'Changed supplier quote')
        with self.assertRaisesRegex(ValueError,'hash'):
            price_draft(draft,price,'2026-09-16',self.evidence)

    def test_template_inputs_keep_quantities_but_cannot_be_priced(self):
        self.template['rows'][0]['parent']='INPUTS'
        draft=template_draft(self.state,self.rules,self.template)
        self.assertEqual(draft['rows'][0]['draft_quantity'],100)
        self.assertEqual(draft['rows'][0]['pricing_role'],'input_only')
        for old_draft in (False,True):
            candidate=copy.deepcopy(draft)
            if old_draft:candidate['rows'][0].pop('pricing_role')
            with self.assertRaisesRegex(ValueError,'not billable'):
                price_draft(candidate,self.pricing(),'2026-09-16',self.evidence)

    def owner_pricing(self):
        record={'source':'Jason, current conversation','recorded_at':'2026-09-10T12:00:00+00:00',
            'answer':'Synthetic owner test rate','rate':2.25}
        path=self.evidence/'owner.json';path.write_text(json.dumps(record))
        pricing=self.pricing();rate=pricing['rates'][0];rate.pop('valid_through')
        rate.update(evidence_kind='jason_approved_rate',date='2026-09-10',
            source_file='owner.json',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            source_rate_field='rate',validity_policy='owner_rate_until_changed',active=True)
        return pricing

    def test_standing_owner_rate_keeps_original_date_and_is_not_supplier_certification(self):
        draft=template_draft(self.state,self.rules,self.template)
        priced=price_draft(draft,self.owner_pricing(),'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual(priced['line_cost'],225)
        self.assertEqual(priced['line_price'],258.75)
        self.assertEqual(priced['price_evidence']['date'],'2026-09-10')
        self.assertFalse(priced['current_price_certified'])
        self.assertIn('supplier pricing not revalidated',priced['price_status'])

    def test_owner_policy_cannot_override_quote_expiry_or_change_recorded_rate(self):
        draft=template_draft(self.state,self.rules,self.template)
        for change in ('kind','expiry','amount','date'):
            pricing=self.owner_pricing();rate=pricing['rates'][0]
            if change=='kind':rate['evidence_kind']='current_supplier_quote'
            if change=='expiry':rate['valid_through']='2026-09-10'
            if change=='amount':rate['unit_price']=3
            if change=='date':rate['date']='2026-09-16'
            with self.assertRaises(ValueError):price_draft(draft,pricing,'2026-09-16',self.evidence)

    def test_inactive_owner_rate_stays_unpriced(self):
        draft=template_draft(self.state,self.rules,self.template)
        pricing=self.owner_pricing();pricing['rates'][0]['active']=False
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertIsNone(row['line_cost'])
        self.assertIn('inactive',row['price_status'])

    def test_nested_owner_rate_requires_exact_source_path_and_value(self):
        draft=template_draft(self.state,self.rules,self.template)
        pricing=self.owner_pricing();path=self.evidence/'owner.json'
        record=json.loads(path.read_text());record['door']={'labor_cost':record.pop('rate')}
        path.write_text(json.dumps(record));rate=pricing['rates'][0]
        rate.update(source_rate_field='door.labor_cost',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]['line_cost'],225)
        for field in ('door.material_cost','door','missing.labor_cost',None,4,''):
            rate['source_rate_field']=field
            with self.assertRaisesRegex(ValueError,'original dated answer'):
                price_draft(draft,pricing,'2026-09-16',self.evidence)

    def test_standing_rate_recalculates_new_quantity_but_never_reuses_missing_quantity(self):
        draft=template_draft(self.state,self.rules,self.template)
        draft['measurement_version']=2;draft['rows'][0]['draft_quantity']=200
        pricing=self.owner_pricing()
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual(row['line_cost'],450)
        draft['rows'][0]['draft_quantity']=None
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertIsNone(row['line_cost']);self.assertIsNone(row['line_price'])
        self.assertEqual(row['unit_cost'],2.25)

    def retail_pricing(self):
        pricing=self.pricing();rate=pricing['rates'][0]
        rate.update(evidence_kind='retail_listing',validity_policy='observation_date_only',
            valid_through=rate['date'],product_id='test-product',tax_included=False,source_file='retail.json')
        record={k:rate[k] for k in ('date','unit_price','unit','source','product_id')}
        record['unit_basis']='Synthetic test product priced per SF'
        path=self.evidence/'retail.json';path.write_text(json.dumps(record))
        rate['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        tax={'plan_sha256':'plan','jurisdiction':'Synthetic jurisdiction','source':'Synthetic tax evidence',
            'percent':8,'effective_from':'2026-07-01','effective_through':'2026-09-30'}
        path=self.evidence/'tax.json';path.write_text(json.dumps(tax))
        rate['purchase_tax']={**tax,'source_file':'tax.json','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return pricing

    def test_retail_tax_applies_once_before_markup_and_preserves_supplier_rate(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual((row['unit_cost'],row['supplier_cost'],row['purchase_tax'],row['line_cost'],row['line_price']),
                         (2.25,225,18,243,279.45))
        self.assertFalse(row['current_price_certified'])
        again=price_draft({'rows':[row],**{k:v for k,v in draft.items() if k!='rows'}},pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual(again['line_cost'],243)
        draft['rows'][0]['draft_quantity']=0
        self.assertEqual(price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]['line_cost'],0)

    def test_retail_observation_does_not_become_a_quote_or_survive_unverified_date(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        row=price_draft(draft,pricing,'2026-09-17',self.evidence)['rows'][0]
        self.assertIsNone(row['line_cost']);self.assertIsNone(row['purchase_tax'])
        for field,value in [('unit_price',3),('product_id','wrong'),('valid_through','2026-09-30'),('tax_included',True)]:
            changed=copy.deepcopy(pricing);changed['rates'][0][field]=value
            with self.assertRaises(ValueError):price_draft(draft,changed,'2026-09-16',self.evidence)

    def test_retail_rejects_changed_or_wrong_project_tax_evidence(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        pricing['rates'][0]['purchase_tax']['percent']=7
        with self.assertRaisesRegex(ValueError,'Purchase tax'):price_draft(draft,pricing,'2026-09-16',self.evidence)
        pricing=self.retail_pricing();path=self.evidence/'tax.json';record=json.loads(path.read_text())
        record['plan_sha256']='different';path.write_text(json.dumps(record))
        pricing['rates'][0]['purchase_tax']['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'Purchase tax'):price_draft(draft,pricing,'2026-09-16',self.evidence)

    def test_retail_tax_rounds_line_subtotal_before_tax_and_markup(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        draft['rows'][0]['draft_quantity']=1.0023
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual((row['supplier_cost'],row['purchase_tax'],row['line_cost'],row['line_price']),(2.26,.18,2.44,2.81))

    def test_retail_recalculates_new_revision_and_withholds_missing_quantity(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        draft['measurement_version']=2;draft['rows'][0]['draft_quantity']=200
        self.assertEqual(price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]['line_cost'],486)
        draft['rows'][0]['draft_quantity']=None
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertIsNone(row['line_cost']);self.assertIsNone(row['purchase_tax'])

    def test_kit_price_refuses_stale_product_or_model(self):
        draft=template_draft(self.state,self.rules,self.template);pricing=self.retail_pricing()
        rate=pricing['rates'][0];rate['model']='selected-model'
        for kind in ('reviewed_kit_purchase','reviewed_item_purchase'):
            draft['rows'][0]['quantity_sources']=[{'kind':kind,
                'product_id':rate['product_id'],'model':'selected-model'}]
            self.assertIsNotNone(price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]['line_cost'])
            for key in ('product_id','model'):
                candidate=copy.deepcopy(pricing);candidate['rates'][0][key]='different-product'
                with self.assertRaisesRegex(ValueError,'identified product'):
                    price_draft(draft,candidate,'2026-09-16',self.evidence)

    def test_supplemental_rate_prices_only_its_explicit_owner(self):
        draft=template_draft(self.state,self.rules,self.template)
        extra={**copy.deepcopy(draft['rows'][0]),'row_id':'supplemental','parent_row_id':'slab'}
        draft['additional_cost_rows']=[extra]
        pricing=self.owner_pricing();pricing['rates'][0]['row_id']='supplemental'
        result=price_draft(draft,pricing,'2026-09-16',self.evidence)
        self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertEqual(result['additional_cost_rows'][0]['line_cost'],225)
        extra['row_id']='template-101'
        with self.assertRaisesRegex(ValueError,'Duplicate cost ownership'):
            price_draft(draft,pricing,'2026-09-16',self.evidence)

    def test_owner_delivery_tax_uses_the_same_line_rounding_without_retaxing_included_rates(self):
        draft=template_draft(self.state,self.rules,self.template)
        tax=self.retail_pricing()['rates'][0]['purchase_tax']
        pricing=self.owner_pricing();pricing['rates'][0].update(purchase_tax=tax,tax_included=False)
        row=price_draft(draft,pricing,'2026-09-16',self.evidence)['rows'][0]
        self.assertEqual((row['line_cost'],row['purchase_tax'],row['line_price']),(243,18,279.45))
        pricing['rates'][0]['tax_included']=True
        with self.assertRaises(ValueError):price_draft(draft,pricing,'2026-09-16',self.evidence)

    def test_changed_geometry_leaves_known_supplemental_rate_unapplied_but_unknown_ids_fail(self):
        draft=template_draft(self.state,self.rules,self.template)
        draft.update(saved_trade_review_required='Changed geometry',withheld_supplemental_cost_ids=['supplemental'])
        pricing=self.owner_pricing();pricing['rates'][0]['row_id']='supplemental'
        result=price_draft(draft,pricing,'2026-09-16',self.evidence)
        self.assertEqual(len(result['unapplied_prices']),1)
        self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertEqual(len(price_draft(result,pricing,'2026-09-16',self.evidence)['unapplied_prices']),1)
        pricing['rates'].append(copy.deepcopy(pricing['rates'][0]))
        with self.assertRaises(ValueError):price_draft(draft,pricing,'2026-09-16',self.evidence)
        pricing['rates']=pricing['rates'][:1];pricing['rates'][0]['row_id']='unknown'
        with self.assertRaises(ValueError):price_draft(draft,pricing,'2026-09-16',self.evidence)

if __name__=='__main__':unittest.main()
