import html
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
LEVEL=Path(__file__).resolve().parents[2]/'levelground'
sys.path.insert(0,str(LEVEL))
from gen_reports import inject


class ReportExport(unittest.TestCase):
    def setUp(self):
        self.template=(LEVEL/'lg_report_template.html').read_text(encoding='utf-8')
        self.pattern=r'<script id="report-data" type="application/json">(.*?)</script>'
        self.report=json.loads(re.search(self.pattern,self.template,re.S).group(1))
        self.payload='</script><img src=x onerror="alert(1)"> -- homeowner & builder'

    def test_report_json_roundtrips_without_script_breakout_or_text_changes(self):
        self.report['questions']=[self.payload]
        result=inject(self.template,self.report)
        embedded=re.search(self.pattern,result,re.S).group(1)
        self.assertNotIn('<',embedded)
        self.assertEqual(json.loads(embedded),self.report)

    def test_missing_or_duplicate_data_block_refused(self):
        block='<script id="report-data" type="application/json">{}</script>'
        for source in ('<html></html>',block+block):
            with self.assertRaises(ValueError):inject(source,self.report)

    def test_actual_renderer_escapes_all_report_text_sinks(self):
        self.report['meta']['prepared_for']=self.payload
        self.report['findings'][0].update(title=self.payload,detail=self.payload,basis=self.payload)
        self.report['quantities'][0].update(item=self.payload,source=self.payload)
        self.report['questions']=[self.payload];self.report['unknowns']=[self.payload]
        script=re.findall(r'<script>(.*?)</script>',self.template,re.S)[-1]
        runner=r'''
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),elements={};
const document={getElementById(id){return elements[id]??=(id==='report-data'
  ?{textContent:JSON.stringify(input.report)}
  :{style:{},classList:{remove(){},toggle(){}},innerHTML:'',textContent:''});},querySelectorAll(){return [];}};
vm.runInNewContext(input.script,{document});
process.stdout.write(JSON.stringify(elements));
'''
        run=subprocess.run(['node','-e',runner],input=json.dumps({'report':self.report,'script':script}),
                           capture_output=True,text=True,encoding='utf-8',check=True)
        elements=json.loads(run.stdout)
        for identity in ('rMeta','findings','qty','questions','unknowns'):
            value=elements[identity]['innerHTML']
            self.assertNotIn('<img',value)
            self.assertIn('&lt;/script&gt;&lt;img',value)
            self.assertIn(self.payload,html.unescape(value))

if __name__=='__main__':unittest.main()
