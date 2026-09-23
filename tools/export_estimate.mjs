import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';

const [snapshotPath,templatePath,output,snapshotHash,templateHash]=process.argv.slice(2);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const snapshotBytes=await fs.readFile(snapshotPath),templateBytes=await fs.readFile(templatePath);
assert.equal(sha(snapshotBytes),snapshotHash);assert.equal(sha(templateBytes),templateHash);
await assert.rejects(fs.access(output));
const {draft,readiness,snapshot_sha256}=JSON.parse(snapshotBytes);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const estimate=wb.worksheets.getItem('Estimate');
if(process.argv.includes('--preview')){
 const preview=await wb.render({sheetName:'Estimate',range:'A3:N10',scale:1});
 await fs.writeFile(output+'.before.png',new Uint8Array(await preview.arrayBuffer()));
 process.exit(0);
}
const notes=wb.worksheets.add('Takeoff Notes'),pending=wb.worksheets.add('Assumptions-to-Confirm');
notes.getRange('A1:F2').values=[['Draft estimate sources',null,null,null,null,null],
 ['Plan SHA256',draft.plan_sha256,'Snapshot SHA256',snapshot_sha256,null,null]];
notes.getRange('A4:F4').values=[['Row ID','Item','Quantity basis and limits','Reviewed cost','Purchase tax %','Price source']];
pending.getRange('A1:D3').values=[['Unresolved estimate work',null,null,null],
 ['System review list. Owner answers remain in the separate question workbook.',null,null,null],
 ['Row ID','Item','Open issues','Warnings']];
const all=[...draft.rows,...(draft.additional_cost_rows??[])];
const noteRow=new Map(all.map((r,i)=>[r.row_id,i+5]));
const sourceText=r=>{
 const p=r.price_evidence;if(!p)return 'Price unavailable';
 return [p.source,p.date,p.source_file,p.quote?.supplier,p.quote?.date,p.quote?.source_file,p.scope_note,p.limitation].filter(Boolean).join('; ');
};
notes.getRange(`A5:F${all.length+4}`).values=all.map(r=>[r.row_id,r.name,
 (r.quantity_sources??[]).map(q=>[q.basis??q.mapping_basis??q.quantity_status,...(q.remaining??[])].filter(Boolean).join(' ')).join('; '),
 r.line_cost??null,r.purchase_tax_percent??0,sourceText(r)]);
const reviewRows=[...readiness.rows,...readiness.additional_cost_rows].filter(r=>r.issues.length||r.warnings.length);
if(reviewRows.length)pending.getRange(`A4:D${reviewRows.length+3}`).values=reviewRows.map(r=>[r.row_id,r.name,r.issues.join('; '),r.warnings.join('; ')]);
const locations=new Map(draft.rows.map(r=>[r.row_id,`'Estimate'!G${r.excel_row}`]));
let extra;
if(draft.additional_cost_rows?.length){
 extra=wb.worksheets.add('Supplemental Costs');
 extra.getRange('A1:I1').values=[['Row ID','Item','Unit','Quantity','Unit cost','Cost','Markup %','Amount','Scope']];
 draft.additional_cost_rows.forEach((r,i)=>locations.set(r.row_id,`'Supplemental Costs'!D${i+2}`));
}
const equal=(cell,value)=>value==null?`${cell}=""`:`AND(ISNUMBER(${cell}),ABS(${cell}-${value})<0.00000001)`;
function costFormula(r,q,rate){
 if(r.line_cost==null)return null;
 const n=noteRow.get(r.row_id),guards=[equal(q,r.draft_quantity),equal(rate,r.unit_cost)];
 for(const id of r.price_evidence?.covered_row_ids??[]){
  const covered=all.find(x=>x.row_id===id);assert(covered&&locations.has(id),'Missing package member '+id);
  guards.push(equal(locations.get(id),covered.draft_quantity));
 }
 if(r.price_evidence?.pricing_basis==='unit_rate'){
  assert(r.draft_quantity!=null&&r.unit_cost!=null,'Unit price needs quantity and rate');
  return `=IF(AND(${guards.join(',')}),ROUND(ROUND(${q}*${rate},2)+ROUND(ROUND(${q}*${rate},2)*'Takeoff Notes'!E${n}/100,2),2),"")`;
 }
 return `=IF(AND(${guards.join(',')},ISNUMBER('Takeoff Notes'!D${n})),'Takeoff Notes'!D${n},"")`;
}
const set=(s,c,v)=>s.getRange(c).values=[[v??null]];
const formula=(s,c,f)=>f?s.getRange(c).formulas=[[f]]:set(s,c,null);
for(const r of draft.rows){
 const n=r.excel_row;
 set(estimate,'A'+n,r.name);set(estimate,'B'+n,r.parent);set(estimate,'I'+n,r.unit);
 set(estimate,'D'+n,r.completion_status?.startsWith('not_applicable')?'Not applicable':'Draft');
 set(estimate,'G'+n,r.draft_quantity);set(estimate,'H'+n,r.unit_cost);
 formula(estimate,'J'+n,costFormula(r,'G'+n,'H'+n));
 formula(estimate,'N'+n,r.line_price==null?null:`=IF(AND(ISNUMBER(J${n}),ISNUMBER(K${n})),ROUND(J${n}*(1+K${n}/100),2),"")`);
 formula(estimate,'L'+n,r.line_price==null?null:`=IF(AND(ISNUMBER(N${n}),ISNUMBER(J${n})),ROUND(N${n}-J${n},2),"")`);
 formula(estimate,'M'+n,r.line_price==null?null:`=IF(AND(ISNUMBER(N${n}),ISNUMBER(G${n}),G${n}<>0),N${n}/G${n},"")`);
}
for(const [i,r] of (draft.additional_cost_rows??[]).entries()){
 const n=i+2;extra.getRange(`A${n}:I${n}`).values=[[r.row_id,r.name,r.unit,r.draft_quantity??null,r.unit_cost??null,null,Number(r.markup_pct),null,r.parent??r.parent_row_id]];
 formula(extra,'F'+n,costFormula(r,'D'+n,'E'+n));
 formula(extra,'H'+n,r.line_price==null?null:`=IF(AND(ISNUMBER(F${n}),ISNUMBER(G${n})),ROUND(F${n}*(1+G${n}/100),2),"")`);
}
for(const [s,last,widths] of [[notes,all.length+4,[32,42,80,16,18,75]],[pending,reviewRows.length+3,[32,42,85,65]]]){
 s.showGridLines=false;s.freezePanes.freezeRows(s===notes?4:3);
 widths.forEach((w,i)=>s.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}${last}`).format.columnWidth=w);
 s.getRange(`A1:${String.fromCharCode(64+widths.length)}${last}`).format.font.name='Arial';
 s.getRange(`A1:${String.fromCharCode(64+widths.length)}${last}`).format.wrapText=true;
 s.getRange(`A1:${String.fromCharCode(64+widths.length)}${last}`).format.autofitRows();
}
notes.getRange(`D5:D${all.length+4}`).setNumberFormat('$#,##0.00');
if(extra){extra.getRange(`A1:I${draft.additional_cost_rows.length+1}`).format.autofitColumns();extra.freezePanes.freezeRows(1);}
wb.recalculate();
const same=(a,b)=>b==null?a==null||a==='':typeof a==='number'&&Math.abs(a-b)<1e-7;
for(const r of draft.rows)for(const [c,k] of [['G','draft_quantity'],['H','unit_cost'],['J','line_cost'],['N','line_price']])
 assert(same(estimate.getRange(c+r.excel_row).values[0][0],r[k]),`${r.row_id} ${k}`);
for(const [i,r] of (draft.additional_cost_rows??[]).entries())for(const [c,k] of [['D','draft_quantity'],['E','unit_cost'],['F','line_cost'],['H','line_price']])
 assert(same(extra.getRange(c+(i+2)).values[0][0],r[k]),`${r.row_id} ${k}`);
if(process.argv.includes('--check-only')){
 console.log(JSON.stringify({template_rows:draft.rows.length,supplemental_rows:draft.additional_cost_rows?.length??0,all_quantities_and_costs_match:true}));
 process.exit(0);
}
await assert.rejects(fs.access(output));
await(await SpreadsheetFile.exportXlsx(wb)).save(output);
const preview=await wb.render({sheetName:'Estimate',range:'A3:N10',scale:1});
await fs.writeFile(output+'.png',new Uint8Array(await preview.arrayBuffer()));
await fs.writeFile(output+'.checks.json',JSON.stringify({snapshot_sha256,source_template_sha256:templateHash,template_rows:draft.rows.length,supplemental_rows:draft.additional_cost_rows?.length??0,all_quantities_and_costs_match:true,estimate_released:false,native_excel_recalculation_verified:false},null,2)+'\n');
console.log(output);
