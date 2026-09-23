import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from package_pricing import price_packages,scope_digest


class InvoiceAllocations(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[
            {'row_id':str(i),'unit':'each','cost_type':'ALLOWANCE' if i==3 else 'SUBCONTRACTOR',
             'parent':'Tile','markup_pct':'8' if i==3 else '7','completion_status':'evidence_in_progress',
             'draft_quantity':None,'line_cost':None,'line_price':None} for i in range(1,5)]}
        self.ledger={'invoices':[]}
        for identity,total,parts in [('2147','12500.00',[('master-labor','6300.00'),('backsplash-labor','1500.00'),
            ('reserved-materials','4200.00'),('prior-backsplash','500.00')]),('2148','206.00',[('net-addition','206.00')])]:
            p=self.root/(identity+'.txt');p.write_text('Synthetic original invoice '+identity)
            self.ledger['invoices'].append({'id':identity,'source_file':p.name,
                'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'total':total,
                'allocations':[{'id':i,'amount':a} for i,a in parts]})
        self.save_ledger()

    def save_ledger(self):
        p=self.root/'allocations.json';p.write_text(json.dumps(self.ledger))
        self.binding={'source_file':p.name,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

    def package(self,row,amount,claims,primary='2147'):
        source=next(i for i in self.ledger['invoices'] if i['id']==primary)
        scope={'plan_sha256':'plan','measurement_version':1,'items':[{'id':'scope','label':'Reviewed allocated scope'}]}
        quote={'id':'quote-'+str(row),'supplier':'Test supplier','source_file':source['source_file'],
            'source_sha256':source['source_sha256'],'date':'2026-09-01','valid_through':'2026-09-30',
            'currency':'USD','total':amount,'reviewed':True,'reviewed_scope_sha256':scope_digest(scope),
            'evidence_kind':'current_subcontractor_quote','scope_items':[{'scope_id':'scope','status':'included','source_ref':'Reviewed invoice lines'}],
            'invoice_allocations':{**self.binding,'claims':[{'invoice_id':i,'allocation_id':a} for i,a in claims]}}
        return {'scope':scope,'quotes':[quote],'quote_id':quote['id'],'row_id':str(row),'covered_row_ids':[str(row)],
            'scope_mapping_reviewed':True,'reviewed_draft_sha256':scope_digest(self.draft),'billing_basis':'fixed_package'}

    def run_packages(self,*packages):return price_packages(self.draft,list(packages),'2026-09-18',self.root)

    def test_distinct_invoice_allocations_and_net_addition_price_once(self):
        result=self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]),
            self.package(2,'1500.00',[('2147','backsplash-labor')]),
            self.package(3,'706.00',[('2147','prior-backsplash'),('2148','net-addition')],primary='2148'))
        self.assertEqual([r['line_cost'] for r in result['rows']],[6300,1500,706,None])
        self.assertEqual([r['line_price'] for r in result['rows']],[6741,1605,762.48,None])
        self.assertEqual(sum(r['line_cost'] or 0 for r in result['rows']),8506)
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertFalse(result['estimate_released']);self.assertIsNone(result['whole_house_total'])
        self.assertTrue(all(r['line_cost'] is None for r in self.draft['rows']))
        self.assertEqual(len(result['rows'][2]['price_evidence']['quote']['invoice_allocations']['claims']),2)

    def test_changed_accounting_allocation_source_rejects_price(self):
        source=self.root/'accounting.json';source.write_text('{"materials":6300}')
        self.ledger['invoices'][0]['allocation_source']={'source_file':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        self.save_ledger();package=self.package(1,'6300.00',[('2147','master-labor')])
        self.assertEqual(self.run_packages(package)['rows'][0]['line_cost'],6300)
        source.write_text('{"materials":6500}')
        with self.assertRaisesRegex(ValueError,'evidence is missing or changed'):self.run_packages(package)

    def test_same_allocation_cannot_price_two_different_rows(self):
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]),self.package(2,'6300.00',[('2147','master-labor')]))

    def test_legacy_whole_source_and_allocation_cannot_overlap_in_either_order(self):
        whole=self.package(1,'12500.00',[('2147','master-labor')]);whole['quotes'][0].pop('invoice_allocations')
        split=self.package(2,'1500.00',[('2147','backsplash-labor')])
        for packages in [(whole,split),(split,whole)]:
            with self.subTest(order=packages[0]['row_id']),self.assertRaises(ValueError):self.run_packages(*packages)

    def test_different_review_partitions_of_same_invoice_cannot_mix(self):
        first=self.package(1,'6300.00',[('2147','master-labor')])
        self.ledger['invoices'][0]['allocations'][0]['id']='renamed-part';self.save_ledger()
        p=self.root/'other.json';p.write_bytes((self.root/'allocations.json').read_bytes())
        second=self.package(2,'6300.00',[('2147','renamed-part')]);second['quotes'][0]['invoice_allocations']['source_file']='other.json'
        self.ledger['invoices'][0]['allocations'][0]['id']='master-labor';self.save_ledger()
        with self.assertRaises(ValueError):self.run_packages(first,second)

    def test_claim_sum_must_equal_quote_total(self):
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.01',[('2147','master-labor')]))

    def test_changed_secondary_original_or_ledger_is_rejected(self):
        package=self.package(1,'706.00',[('2147','prior-backsplash'),('2148','net-addition')])
        for name in ['2148.txt','allocations.json']:
            p=self.root/name;original=p.read_bytes();p.write_bytes(original+b'changed')
            with self.subTest(file=name),self.assertRaises(ValueError):self.run_packages(package)
            p.write_bytes(original)

    def test_invalid_partition_or_amounts_are_rejected(self):
        original=copy.deepcopy(self.ledger)
        for value in ['0','-1','6300.001','NaN','Infinity',True,'6400.00']:
            self.ledger=copy.deepcopy(original);self.ledger['invoices'][0]['allocations'][0]['amount']=value;self.save_ledger()
            with self.subTest(value=value),self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))
        self.ledger=copy.deepcopy(original);self.ledger['invoices'][0]['allocations'][1]['id']='master-labor';self.save_ledger()
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))

    def test_unknown_duplicate_or_empty_claims_are_rejected(self):
        for claims in [[],[('2147','missing')],[('missing','master-labor')],[('2147','master-labor')]*2]:
            with self.subTest(claims=claims),self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',claims))

    def test_primary_document_must_be_in_claims(self):
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'206.00',[('2148','net-addition')],primary='2147'))

    def test_duplicate_invoice_identity_or_document_is_rejected(self):
        self.ledger['invoices'].append(copy.deepcopy(self.ledger['invoices'][0]));self.save_ledger()
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))

    def test_allocations_require_fixed_package_billing(self):
        p=self.package(1,'6300.00',[('2147','master-labor')]);p.pop('billing_basis')
        with self.assertRaises(ValueError):self.run_packages(p)

    def test_whole_source_cannot_overlap_a_secondary_claim(self):
        whole=self.package(1,'12500.00',[('2147','master-labor')]);whole['quotes'][0].pop('invoice_allocations')
        split=self.package(2,'706.00',[('2147','prior-backsplash'),('2148','net-addition')],primary='2148')
        for packages in [(whole,split),(split,whole)]:
            with self.subTest(order=packages[0]['row_id']),self.assertRaises(ValueError):self.run_packages(*packages)

    def test_ledger_and_original_sources_cannot_escape_evidence_root(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);outside=Path(tmp.name)
        original=self.root/'2147.txt';escaped=outside/original.name;escaped.write_bytes(original.read_bytes())
        self.ledger['invoices'][0]['source_file']=str(escaped);self.save_ledger()
        with self.assertRaises(ValueError):self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))
        self.ledger['invoices'][0]['source_file']=original.name;self.save_ledger()
        package=self.package(1,'6300.00',[('2147','master-labor')])
        escaped=outside/'allocations.json';escaped.write_bytes((self.root/'allocations.json').read_bytes())
        package['quotes'][0]['invoice_allocations']['source_file']=str(escaped)
        with self.assertRaises(ValueError):self.run_packages(package)

    def test_contract_plus_hardware_excludes_repeated_completion_balance(self):
        first,second=self.ledger['invoices']
        first.update(total='16900.00',allocations=[{'id':'contract','amount':'16900.00'}])
        second.update(total='4725.00',allocations=[{'id':'balance','amount':'4225.00',
            'settles':{'invoice_id':'2147','allocation_id':'contract'}},{'id':'hardware','amount':'500.00'}])
        self.save_ledger()
        package=self.package(3,'17400.00',[('2147','contract'),('2148','hardware')])
        result=self.run_packages(package)
        self.assertEqual(result['rows'][2]['line_cost'],17400)
        self.assertEqual(result['rows'][2]['line_price'],18792)
        with self.assertRaisesRegex(ValueError,'already included'):
            self.run_packages(package,self.package(2,'4225.00',[('2148','balance')],primary='2148'))

    def test_settlement_reference_must_exist_and_cover_amount(self):
        self.ledger['invoices'][1]['allocations'][0]['settles']={'invoice_id':'2147','allocation_id':'prior-backsplash'}
        original=copy.deepcopy(self.ledger)
        for reference in [None,{}, {'invoice_id':'absent','allocation_id':'prior-backsplash'},
                          {'invoice_id':'2147','allocation_id':'absent'},
                          {'invoice_id':'2148','allocation_id':'net-addition'}]:
            self.ledger=copy.deepcopy(original);self.ledger['invoices'][1]['allocations'][0]['settles']=reference;self.save_ledger()
            with self.subTest(reference=reference),self.assertRaises(ValueError):
                self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))
        self.ledger=copy.deepcopy(original);self.ledger['invoices'][1]['total']='501.00'
        self.ledger['invoices'][1]['allocations'][0]['amount']='501.00';self.save_ledger()
        with self.assertRaisesRegex(ValueError,'contract amount'):
            self.run_packages(self.package(1,'6300.00',[('2147','master-labor')]))


    def test_combined_settlements_cannot_hide_amounts_above_contract(self):
        first,second=self.ledger['invoices']
        first.update(total='1000.00',allocations=[{'id':'contract','amount':'1000.00'}])
        target={'invoice_id':'2147','allocation_id':'contract'}
        second.update(total='1200.00',allocations=[
            {'id':'progress','amount':'600.00','settles':target},
            {'id':'completion','amount':'600.00','settles':target}])
        self.save_ledger()
        with self.assertRaisesRegex(ValueError,'Combined settlements exceed'):
            self.run_packages(self.package(1,'1000.00',[('2147','contract')]))
        second['total']='1000.00';second['allocations'][1]['amount']='400.00'
        self.save_ledger()
        result=self.run_packages(self.package(1,'1000.00',[('2147','contract')]))
        self.assertEqual(result['rows'][0]['line_cost'],1000)


if __name__=='__main__':unittest.main()
