"""Create a source-bound new-plan job with company practices and sheet inventory.

Exact sheet titles are routing candidates, not automatic geometry certification.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
import fitz
from company_profile import DEFAULT_PROFILE, initialize, resolve
from door_specifications import door_core_specifications
from door_hardware_specifications import door_hardware_specifications
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from levelground.local_requirements import requirements_context

TITLES={'FLOOR PLAN':'floor','FOUNDATION WALL PLAN':'foundation','FOUNDATION PLAN':'foundation',
    'FIRST FLOOR PLAN':'floor','MAIN FLOOR PLAN':'floor','SECOND FLOOR PLAN':'floor',
    'BASEMENT FLOOR PLAN':'floor',
    'ROOF PLAN':'roof','ELECTRICAL PLAN':'electrical','SQFT PLANS':'area_schedule','SQFT SHEET':'area_schedule',
    'SITE PLAN':'site','EXTERIOR ELEVATIONS':'elevations','INTERIOR ELEVATIONS':'interior_elevations',
    'FLOOR & CEILING FRAMING PLANS':'framing'}


def ocr_page(page):
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return '', 'OCR dependency unavailable'
    if not shutil.which('tesseract'):
        return '', 'Tesseract executable unavailable'
    pix=page.get_pixmap(matrix=fitz.Matrix(150/72,150/72),colorspace=fitz.csRGB,alpha=False)
    try:
        with Image.frombytes('RGB',(pix.width,pix.height),pix.samples) as image:
            text=pytesseract.image_to_string(image,config='--psm 11',timeout=45)
        return text,None
    except (RuntimeError,pytesseract.TesseractError) as exc:
        return '',str(exc)


def inventory(plan):
    pages=[];roles={};area_references=[]
    with fitz.open(plan) as doc:
        if doc.needs_pass:raise ValueError('Plan PDF requires a password')
        if not len(doc):raise ValueError('Plan PDF contains no pages')
        for i,page in enumerate(doc):
            text=page.get_text();method='native_pdf_text';ocr_issue=None
            if not text.strip():text,ocr_issue=ocr_page(page);method='local_ocr'
            lines=[' '.join(line.upper().split()) for line in text.splitlines()]
            # Some title blocks wrap FOUNDATION / PLAN onto adjacent text lines.
            # Match complete known titles, never arbitrary occurrences in notes.
            title_lines=set(lines)
            title_lines.update(a+' '+b for a,b in zip(lines,lines[1:]) if a and b)
            is_index=bool({'INDEX OF DRAWINGS','DRAWING INDEX','SHEET INDEX','COVER SHEET'}.intersection(title_lines))
            found=sorted({TITLES[line] for line in title_lines if line in TITLES}) if not is_index else []
            for role in found:roles.setdefault(role,[]).append(i+1)
            if 'area_schedule' in found and method=='native_pdf_text':
                from jnj_takeoff import read_sqft_schedule, framed_under_roof_sf
                schedule=read_sqft_schedule(page)
                area_references.append({'page':i+1,'rows':schedule,
                    'under_roof_reference_sf':framed_under_roof_sf(schedule) if schedule else None,
                    'source':'printed_native_text_schedule','use':'comparison_only',
                    'measured_from_geometry':False,'certified':False,
                    'remaining':'Review table extraction and compare with independently measured geometry; do not price from this reference.'})
            pages.append({'page':i+1,'width_pt':page.rect.width,'height_pt':page.rect.height,
                'text_characters':sum(len(s) for s in lines),'role_candidates':found,
                'text_method':method,'extracted_text':text,'ocr_issue':ocr_issue,
                'drawing_index':is_index,'image_review_required':True,
                'text_extraction_empty':not any(lines)})
    return {'pages':pages,'role_candidates':roles,'unique_role_pages':{k:v[0] for k,v in roles.items() if len(v)==1},
        'roles_requiring_disambiguation':{k:v for k,v in roles.items() if len(v)>1},
        'area_schedule_references':area_references,
        'measured_quantities':{},'current_prices':{},'whole_estimate_total':None,'estimate_released':False,
        'remaining':['Verify page roles and revision/redlines visually.','Verify scales and measure each applicable scope.',
                     'Resolve plan-specific specifications against company defaults.','Obtain current dated pricing and verify complete assembly ownership.']}


def create_job(plan,job,profile=DEFAULT_PROFILE,inputs=None):
    """Publish completed intake together so failed uploads can be retried."""
    job=Path(job)
    if job.exists():raise FileExistsError('Existing job preserved; use a new job directory')
    job.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.intake-',dir=job.parent) as scratch:
        staged=Path(scratch)/'job'
        result=_create_job(plan,staged,profile,inputs,final_job=job)
        if job.exists():raise FileExistsError('Existing job preserved; use a new job directory')
        staged.rename(job)
    return {**result,'job':str(job.resolve()),'company_intake':str((job/'estimate_intake.json').resolve())}


def _create_job(plan,job,profile=DEFAULT_PROFILE,inputs=None,final_job=None):
    plan=Path(plan);job=Path(job);inputs=inputs or {}
    if job.exists():raise FileExistsError('Existing job preserved; use a new job directory')
    resolve(json.loads(Path(profile).read_bytes()),inputs.get('facts'),inputs.get('project_overrides'))
    source_sha=hashlib.sha256(plan.read_bytes()).hexdigest()
    value=inventory(plan)
    job.mkdir(parents=True)
    copied=job/'plan.pdf';shutil.copyfile(plan,copied)
    if hashlib.sha256(copied.read_bytes()).hexdigest()!=source_sha:
        raise ValueError('Source plan changed during intake; retry with a stable source PDF')
    intake=initialize(copied,job,profile,inputs.get('facts'),inputs.get('project_overrides'))
    if final_job is not None:
        record=json.loads(intake.read_bytes())
        record['plan_file']=str((final_job/'plan.pdf').resolve())
        intake.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    value['plan_sha256']=hashlib.sha256(copied.read_bytes()).hexdigest()
    value['company_intake']='estimate_intake.json'
    intake_bytes = intake.read_bytes()
    doors = door_core_specifications(json.loads(intake_bytes), inputs.get('door_schedule'))
    if inputs.get('door_schedule') is not None:
        (job/'door_schedule.json').write_text(json.dumps(inputs['door_schedule'],indent=2)+'\n',encoding='utf-8')
    doors['company_intake_sha256'] = hashlib.sha256(intake_bytes).hexdigest()
    (job/'door_core_specifications.json').write_text(json.dumps(doors,indent=2)+'\n',encoding='utf-8')
    value['door_core_specifications'] = 'door_core_specifications.json'
    hardware = door_hardware_specifications(json.loads(intake_bytes), inputs.get('door_schedule'))
    hardware['company_intake_sha256'] = hashlib.sha256(intake_bytes).hexdigest()
    (job/'door_hardware_specifications.json').write_text(json.dumps(hardware,indent=2)+'\n',encoding='utf-8')
    value['door_hardware_specifications'] = 'door_hardware_specifications.json'
    registry=Path(__file__).resolve().parents[1]/'levelground/data/official-requirements.json'
    registry_bytes=registry.read_bytes()
    local=requirements_context(inputs.get('jurisdiction',{}),json.loads(registry_bytes),date.today().isoformat())
    local['registry_sha256']=hashlib.sha256(registry_bytes).hexdigest()
    local['plan_sha256']=value['plan_sha256']
    local['project_basis']=inputs.get('jurisdiction',{})
    (job/'official_requirements_snapshot.json').write_bytes(registry_bytes)
    (job/'local_requirements.json').write_text(json.dumps(local,indent=2)+'\n',encoding='utf-8')
    value['local_requirements']='local_requirements.json'
    value['local_requirements_sha256']=hashlib.sha256((job/'local_requirements.json').read_bytes()).hexdigest()
    (job/'plan_inventory.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return {'job':str(job.resolve()),'company_intake':str(intake.resolve()),'page_count':len(value['pages']),
        'unique_role_pages':value['unique_role_pages'],'estimate_released':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True);parser.add_argument('--job-dir',required=True)
    parser.add_argument('--profile',default=str(DEFAULT_PROFILE));parser.add_argument('--project-inputs')
    parser.add_argument('--measure-draft',action='store_true',help='Run initial engine measurements and prepare editable candidates')
    args=parser.parse_args()
    inputs=json.loads(Path(args.project_inputs).read_text(encoding='utf-8')) if args.project_inputs else None
    result=create_job(args.plan,args.job_dir,args.profile,inputs)
    if args.measure_draft:
        from new_plan_measure import measure_job
        result['draft_takeoff']=measure_job(args.job_dir)
    print(json.dumps(result))
