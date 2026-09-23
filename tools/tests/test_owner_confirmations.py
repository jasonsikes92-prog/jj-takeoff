import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.owner_confirmations import collect,retain,HEADERS


class OwnerConfirmations(unittest.TestCase):
    def setUp(self):
        self.catalog={'project':'Roberts','roberts':[
            ['R1','Height','How high?','Exact inches','source1'],
            ['R2','Doors','How many?','Whole units','source2']],
            'later':[['L1','Region','Where?','States','source3']]}
        self.sheets={name:{'headers':HEADERS.copy(),'rows':[
            {'row':i+6,'values':q[:4]+[None],'answer_type':'n','number_format':'General'}
            for i,q in enumerate(self.catalog[key])]}
            for name,key in [('Roberts questions','roberts'),('Later business decisions','later')]}

    def test_blank_zero_unknown_and_false_are_distinct(self):
        blank=collect(self.catalog,self.sheets);self.assertEqual(blank['unanswered_question_ids'],['R1','R2','L1'])
        self.sheets['Roberts questions']['rows'][0]['values'][4]=0
        self.sheets['Roberts questions']['rows'][1]['values'][4]=' Unknown '
        self.sheets['Later business decisions']['rows'][0]['values'][4]=False
        result=collect(self.catalog,self.sheets)
        self.assertEqual(result['answered_count'],3);self.assertEqual(result['pending_application_count'],2)
        self.assertEqual(result['unresolved_answer_count'],1)
        self.assertEqual([a['answer'] for a in result['answers']],[0,' Unknown ',False])
        self.assertEqual([a['scope'] for a in result['answers']],['project','project','business'])

    def test_sorted_rows_preserve_identity_and_percentage_format(self):
        row=self.sheets['Roberts questions']['rows'][0]
        row.update(number_format='0%',answer_type='n');row['values'][4]=.2
        self.sheets['Roberts questions']['rows'].reverse()
        result=collect(self.catalog,self.sheets)
        self.assertEqual(result['answers'][0]['question_id'],'R1')
        self.assertEqual(result['answers'][0]['answer'],.2)
        self.assertEqual(result['answers'][0]['answer_number_format'],'0%')

    def test_project_only_four_field_catalog(self):
        self.catalog['later']=[]
        self.catalog['roberts']=[q[:4] for q in self.catalog['roberts']]
        del self.sheets['Later business decisions']
        result=collect(self.catalog,self.sheets)
        self.assertEqual(result['question_count'],2)
        self.assertEqual(result['unanswered_question_ids'],['R1','R2'])
        self.sheets['Roberts questions']['rows'][0]['values'][4]='Unknown'
        result=collect(self.catalog,self.sheets)
        self.assertEqual(result['unresolved_answer_count'],1)
        self.assertIsNone(result['answers'][0]['source_reference'])
        self.assertFalse(result['answers'][0]['applied_to_estimate'])

    def test_optional_source_and_malformed_catalog(self):
        self.sheets['Roberts questions']['rows'][0]['values'][4]='108 inches'
        self.assertEqual(collect(self.catalog,self.sheets)['answers'][0]['source_reference'],'source1')
        for question in [self.catalog['roberts'][0][:3],self.catalog['roberts'][0]+['extra']]:
            catalog=copy.deepcopy(self.catalog);catalog['roberts'][0]=question
            with self.assertRaisesRegex(ValueError,'four fields'):collect(catalog,self.sheets)

    def test_project_only_rejects_extra_sheets(self):
        self.catalog['later']=[]
        with self.assertRaisesRegex(ValueError,'sheets differ'):collect(self.catalog,self.sheets)

    def test_issued_ledge_headings_preserve_answer_column_and_identity(self):
        sheet=self.sheets['Roberts questions']
        sheet['headers']=['ID','Topic','Question','Already saved / context','Jason’s answer']
        sheet['rows'][0]['values'][4]='Starts at footing'
        result=collect(self.catalog,self.sheets)
        self.assertEqual(result['answers'][0]['answer'],'Starts at footing')
        self.assertEqual(result['answers'][0]['question_id'],'R1')
        sheet['headers'][3],sheet['headers'][4]=sheet['headers'][4],sheet['headers'][3]
        with self.assertRaisesRegex(ValueError,'headings changed'):collect(self.catalog,self.sheets)

    def test_changed_questions_missing_duplicate_and_unknown_ids_rejected(self):
        original=copy.deepcopy(self.sheets)
        for action in ['question','missing','duplicate','unknown','header','sheet']:
            sheets=copy.deepcopy(original);rows=sheets['Roberts questions']['rows']
            if action=='question':rows[0]['values'][2]='Different meaning'
            elif action=='missing':rows.pop()
            elif action=='duplicate':rows.append(copy.deepcopy(rows[0]))
            elif action=='unknown':rows[0]['values'][0]='R999'
            elif action=='header':sheets['Roberts questions']['headers'][4]='Not the answer'
            else:del sheets['Later business decisions']
            with self.assertRaises(ValueError):collect(self.catalog,sheets)

    def test_formulas_errors_and_orphan_answers_rejected(self):
        for kind in ['f','e']:
            row=self.sheets['Roberts questions']['rows'][0]
            row['values'][4]='=1+1' if kind=='f' else '#REF!';row['answer_type']=kind
            with self.assertRaises(ValueError):collect(self.catalog,self.sheets)
        row['values']=[None,None,None,None,'Orphan answer'];row['answer_type']='s'
        with self.assertRaises(ValueError):collect(self.catalog,self.sheets)

    def test_immutable_revisions_idempotence_and_company_default_boundary(self):
        self.sheets['Roberts questions']['rows'][0]['values'][4]='Use 108 inches as company default'
        result=collect(self.catalog,self.sheets);raw=b'original workbook evidence'
        parsed=copy.deepcopy(result);result['question_catalog']=self.catalog
        result['workbook_sha256']=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as temp, patch('tools.owner_confirmations.read_workbook',return_value=parsed) as reader:
            first=retain(result,raw,temp);second=retain(result,raw,temp)
            self.assertEqual(first,second);self.assertFalse(first['company_profile_changed'])
            revised=copy.deepcopy(result);revised['answers'][0]['answer']='109.125 inches'
            with self.assertRaisesRegex(ValueError,'differs from its workbook'):retain(revised,raw,temp)
            revised_raw=b'revised workbook evidence'
            revised['workbook_sha256']=hashlib.sha256(revised_raw).hexdigest()
            reader.return_value={k:v for k,v in revised.items() if k in parsed}
            new=retain(revised,revised_raw,temp)
            self.assertNotEqual(first['submission_id'],new['submission_id'])
            self.assertEqual(json.loads(Path(first['record']).read_text())['submission'],result)
            self.assertEqual(len(list((Path(temp)/'owner_answer_submissions').glob('*.json'))),2)
            evidence=Path(first['record']).with_suffix('.xlsx');evidence.write_bytes(b'changed')
            reader.return_value=parsed
            with self.assertRaisesRegex(ValueError,'evidence changed'):retain(result,raw,temp)

    def test_empty_submission_makes_no_directory_and_changed_bytes_rejected(self):
        result=collect(self.catalog,self.sheets);raw=b'evidence'
        parsed=copy.deepcopy(result);result['question_catalog']=self.catalog
        result['workbook_sha256']=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as temp, patch('tools.owner_confirmations.read_workbook',return_value=parsed):
            self.assertFalse(retain(result,raw,temp)['saved'])
            self.assertEqual(list(Path(temp).iterdir()),[])
            with self.assertRaises(ValueError):retain(result,b'other',temp)


if __name__=='__main__':unittest.main()
