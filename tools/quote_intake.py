"""Preserve a received quote and prepare source-linked, unreviewed comparison data."""
import hashlib
import json
import re
from pathlib import Path
import fitz

from bid_comparison import scope_digest,required_scope_items
from quote_table_candidates import extract_tables,native_tables
from quote_measurement_terms import extract_terms


def total_candidates(pages):
    """Retain every explicitly labeled dollar total, without choosing among them."""
    pattern=re.compile(r'^[ \t]*(?:grand total|total price|total)[ \t]*:?[ \t]*(?:\n[ \t]*)?\$[ \t]*'
                       r'(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2})[ \t]*$',re.I|re.M)
    found=[]
    for page in pages:
        for match in pattern.finditer(page['text']):
            found.append({'field':'total','value':match['amount'].replace(',',''),
                          'currency_symbol':'$','currency_confirmed':False,
                          'page':page['page'],'line':page['text'][:match.start()].count('\n')+1,
                          'source_text':match.group().strip(),'reviewed':False})
    return found


def extract_document_pages(raw, suffix, max_pages=250, max_text_characters=2000000):
    """Extract source text only; a text layer is not proof of visual completeness."""
    if suffix.lower()=='.pdf':
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            if pdf.needs_pass:raise ValueError('Encrypted document needs an accessible copy')
            if len(pdf)>max_pages:raise ValueError('Document exceeds the automatic page limit')
            pages=[];characters=0
            for i,page in enumerate(pdf):
                text=page.get_text();characters+=len(text)
                if characters>max_text_characters:raise ValueError('Document exceeds the automatic text limit')
                words=[list(w[:5]) for w in page.get_text('words')]
                pages.append({'page':i+1,'source_ref':f'page {i+1}','text':text,
                              'words':words,'width':page.rect.width,'tables':native_tables(page,words),
                              'extraction_method':'native_pdf_text'})
    elif suffix.lower()=='.txt':
        text=raw.decode('utf-8-sig')
        if len(text)>max_text_characters:raise ValueError('Document exceeds the automatic text limit')
        pages=[{'page':1,'source_ref':'text document','text':text,'extraction_method':'utf8_text'}]
    else:raise ValueError('Automatic text extraction supports PDF and UTF-8 text documents')
    if not pages:raise ValueError('Document contains no pages')
    return pages


def intake_quote(document, folder, scope, quote_id, supplier=None):
    document=Path(document);folder=Path(folder)
    if folder.exists():raise FileExistsError('Existing quote intake preserved; use a new revision folder')
    if not isinstance(quote_id,str) or not quote_id.strip():raise ValueError('Quote identity required')
    if supplier is not None and (not isinstance(supplier,str) or not supplier.strip()):
        raise ValueError('Supplier must be a name or unknown')
    ids=[item['id'] for item in required_scope_items(scope)]
    if not ids or any(not isinstance(i,str) or not i.strip() for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Unique scope item identities required')
    if not scope.get('plan_sha256') or type(scope.get('measurement_version')) is not int or scope['measurement_version']<1:
        raise ValueError('Drawing and measurement revision required')
    raw=document.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    suffix=document.suffix.lower()
    pages=extract_document_pages(raw,suffix)
    pricing=extract_tables(pages)
    terms=extract_terms(pages)
    filename='source'+suffix
    quote={'id':quote_id.strip(),'supplier':supplier,'source_file':filename,'source_sha256':digest,
           'date':None,'valid_through':None,'currency':None,'total':None,
           'reviewed':False,'reviewed_scope_sha256':None,'evidence_kind':'unclassified',
           'scope_items':[{'scope_id':i,'status':'unknown','source_ref':None,'note':''} for i in ids]}
    summary={'source_sha256':digest,'original_filename':document.name,
             'requested_scope_sha256':scope_digest(scope),'pages':len(pages),
             'pages_needing_visual_or_ocr_review':[p['page'] for p in pages if not p['text'].strip()],
             'pricing_candidate_count':len(pricing['pricing_candidates']),
             'measurement_term_candidate_count':len(terms['candidates']),
             'status':'unreviewed','automatic_scope_assertions':0,'purchase_authorized':False}
    # Parse and validate before creating any output. Never overwrite an older intake.
    folder.mkdir(parents=True)
    (folder/filename).write_bytes(raw)
    for name,value in [('scope.json',scope),('quotes.json',[quote]),
                       ('field_candidates.json',{'source_sha256':digest,'candidates':total_candidates(pages)}),
                       ('pricing_candidates.json',{'source_sha256':digest,**pricing}),
                       ('measurement_term_candidates.json',{'source_sha256':digest,**terms}),
                       ('source_pages.json',{'source_sha256':digest,'pages':pages}),('intake.json',summary)]:
        (folder/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document',required=True);parser.add_argument('--folder',required=True)
    parser.add_argument('--scope',required=True);parser.add_argument('--quote-id',required=True)
    parser.add_argument('--supplier')
    args=parser.parse_args()
    print(json.dumps(intake_quote(args.document,args.folder,
        json.loads(Path(args.scope).read_text(encoding='utf-8')),args.quote_id,args.supplier)))
