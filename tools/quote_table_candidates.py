"""Source-positioned candidates from explicit quantity/rate/amount PDF tables."""
import re
from decimal import Decimal,ROUND_HALF_UP,localcontext
from bfs_invoice import parse_page as parse_bfs,HEADERS as BFS_HEADERS,EDGES as BFS_EDGES

HEADERS={'description':'description','item':'description','qty':'quantity','quantity':'quantity',
    'rate':'unit_rate','unit price':'unit_rate','unit rate':'unit_rate',
    'line total':'amount','amount':'amount','total':'amount',
    'unit':'quantity_unit','units':'quantity_unit','uom':'quantity_unit','u/m':'quantity_unit'}
SUMMARIES={'subtotal','tax','total','grand total','amount paid','amount due','amount due (usd)'}


def explicit_unit(text):
    raw=' '.join(text.strip().upper().split())
    unit={**dict.fromkeys(('EA','EACH'),'each'),**dict.fromkeys(('LF','LINEAR FEET','LIN FT'),'linear_ft'),
        **dict.fromkeys(('SF','SQ FT','SQFT','SQUARE FEET'),'sq_ft'),
        'BOX':'box','PKG':'package'}.get(raw)
    return {'quantity_unit_as_printed':text or None,'quantity_unit':unit,
            'billing_basis':unit if unit!='sq_ft' else None}


def bfs_form(words):return set(BFS_HEADERS)<={w[4] for w in words}


def bfs_candidates(page):
    words=page.get('words',[])
    if not bfs_form(words):return None
    try:rows=parse_bfs(words,page.get('width',0))
    except ValueError as exc:
        return [],[{'page':page['page'],'bbox':position(words),'source_text':'BFS invoice table',
            'reviewed':False,'reason':str(exc)}]
    candidates=[]
    for row in rows:
        source=[w for w in words if abs(w[1]-row['source_row_y'])<=.501]
        cells={}
        for field,left,right in zip(('ordered_quantity','quantity','backorder_quantity','sku','description','quantity_unit','unit_rate','amount'),BFS_EDGES,BFS_EDGES[1:]):
            cell=[w for w in source if left<=w[0]<right]
            if cell:cells[field]={'text':' '.join(w[4] for w in sorted(cell,key=lambda w:w[0])),'bbox':position(cell)}
        expected=(Decimal(row['shipped_quantity'])*Decimal(row['historical_unit_price'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        candidates.append({'page':page['page'],'bbox':position(source),'source_text':' '.join(w[4] for w in sorted(source,key=lambda w:w[0])),
            'description':row['description'],'quantity':str(row['shipped_quantity']),
            'unit_rate':row['historical_unit_price'],'amount':row['historical_extension'],
            **explicit_unit(row['unit']),'quantity_role':'shipped',
            'ordered_quantity':row['ordered_quantity'],'backorder_quantity':row['backorder_quantity'],'sku':row['sku'],
            'cell_sources':cells,'scope_ids':[],'reviewed':False,'currency_confirmed':False,
            'calculated_amount':format(expected,'f'),'arithmetic_matches':expected==Decimal(row['historical_extension']),
            'extraction_method':'supported_bfs_invoice_columns','document_kind_candidate':'supplier_invoice'})
    return candidates,[]


def native_tables(page,words):
    """Capture ruled cells while the PDF page is live, including wrapped descriptions."""
    labels={w[4].lower().rstrip(':') for w in words}
    if bfs_form(words):return []
    if not labels&{'description','item'} or not labels&{'total','amount'}:return []
    tables=[]
    for table in page.find_tables(strategy='lines').tables:
        texts=table.extract()
        tables.append({'bbox':list(table.bbox),'rows':[
            {'bbox':list(row.bbox),'cells':[{'bbox':None if box is None else list(box),'text':text or ''}
                for box,text in zip(row.cells,texts[index])]}
            for index,row in enumerate(table.rows)]})
    return tables


def numeric(text):
    text=text.strip()
    negative=text.startswith('(') and text.endswith(')')
    if negative:text=text[1:-1]
    if text.startswith('$'):text=text[1:].strip()
    if negative and text.startswith('-'):return None
    if not re.fullmatch(r'-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',text):return None
    value=Decimal(text.replace(',',''))
    return format(-value if negative else value,'f')


def lines(words):
    rows=[]
    for word in sorted(words,key=lambda w:(w[1],w[0])):
        # Use top edges: body fonts can differ slightly between text and numbers.
        if not rows or abs(word[1]-rows[-1][0][1])>2:rows.append([])
        rows[-1].append(word)
    return [sorted(row,key=lambda w:w[0]) for row in rows]


def header_columns(row):
    columns=[];i=0
    while i<len(row):
        two=' '.join(w[4].lower().rstrip(':') for w in row[i:i+2])
        one=row[i][4].lower().rstrip(':')
        count=2 if two in HEADERS else 1
        label=two if count==2 else one
        if label not in HEADERS:return None
        group=row[i:i+count]
        columns.append({'field':HEADERS[label],'label':' '.join(w[4] for w in group),
                        'bbox':[group[0][0],min(w[1] for w in group),group[-1][2],max(w[3] for w in group)]})
        i+=count
    if sorted(c['field'] for c in columns) not in (['amount','description','quantity','unit_rate'],
            ['amount','description','quantity','quantity_unit','unit_rate']):return None
    return columns


def position(row):
    return [min(w[0] for w in row),min(w[1] for w in row),max(w[2] for w in row),max(w[3] for w in row)]


def ruled_candidates(page):
    candidates=[];amounts=[];unparsed=[];headers=[];bounds=[]
    for table in page.get('tables',[]):
        mapping=None;header=None;ended=False
        for row in table['rows']:
            values=[' '.join(c['text'].split()).lower().rstrip(':') for c in row['cells']]
            fields=[HEADERS.get(v) for v in values if v]
            if fields and None not in fields and sorted(fields) in (
                    ['amount','description'],['amount','description','quantity','unit_rate'],
                    ['amount','description','quantity','quantity_unit','unit_rate']):
                mapping={i:HEADERS[v] for i,v in enumerate(values) if v}
                header={'page':page['page'],'bbox':row['bbox'],'source_text':' | '.join(c['text'] for c in row['cells']),
                    'reviewed':False,'extraction_method':'ruled_pdf_cells'}
                headers.append(header);bounds.append(table['bbox']);ended=False;continue
            if mapping is None or not any(values):continue
            source={'page':page['page'],'bbox':row['bbox'],'source_text':' | '.join(c['text'] for c in row['cells']),
                    'reviewed':False,'extraction_method':'ruled_pdf_cells'}
            if any(c['text'].strip() and i not in mapping for i,c in enumerate(row['cells'])):
                unparsed.append({**source,'reason':'Nonempty table column has no supported header'});continue
            cells={field:row['cells'][i] for i,field in mapping.items()}
            description=cells['description']['text'].strip()
            numbers={key:numeric(cells[key]['text']) if key in cells else None for key in ('quantity','unit_rate','amount')}
            label=' '.join(description.split()).lower().rstrip(':')
            if label in SUMMARIES and numbers['amount'] is not None:
                amounts.append({**source,'label':label,'value':numbers['amount'],
                    'currency_symbol':'$' if '$' in cells['amount']['text'] else None,'currency_confirmed':False})
                ended=True;continue
            if (ended or not description or any(c['bbox'] is None for c in cells.values())
                    or any(numbers[k] is None for k in cells if k in numbers)):
                unparsed.append({**source,'reason':'Table row needs review; numeric cells, boundaries or table continuation are unresolved'});continue
            expected=None
            if numbers['quantity'] is not None and numbers['unit_rate'] is not None:
                with localcontext() as context:
                    context.prec=max(28,len(numbers['quantity'])+len(numbers['unit_rate'])+4)
                    expected=(Decimal(numbers['quantity'])*Decimal(numbers['unit_rate'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            candidates.append({**source,'description':description,**numbers,'cell_sources':cells,
                **explicit_unit(cells.get('quantity_unit',{}).get('text','')),'scope_ids':[],
                'currency_confirmed':False,'calculated_amount':None if expected is None else format(expected,'f'),
                'arithmetic_matches':None if expected is None else expected==Decimal(numbers['amount']),
                'header_bbox':header['bbox']})
    return candidates,amounts,unparsed,headers,bounds


def extract_tables(pages):
    candidates=[];amounts=[];unparsed=[];headers=[]
    for page in pages:
        supplier=bfs_candidates(page)
        if supplier is not None:
            candidates.extend(supplier[0]);unparsed.extend(supplier[1]);continue
        ruled,totals,unknown,found_headers,bounds=ruled_candidates(page)
        candidates.extend(ruled);amounts.extend(totals);unparsed.extend(unknown);headers.extend(found_headers)
        words=[w for w in page.get('words',[]) if not any(
            b[0]<=(w[0]+w[2])/2<=b[2] and b[1]<=(w[1]+w[3])/2<=b[3] for b in bounds)]
        columns=None
        for row in lines(words):
            text=' '.join(w[4] for w in row)
            source={'page':page['page'],'bbox':position(row),'source_text':text,'reviewed':False}
            found=header_columns(row)
            if found:
                columns=found;headers.append({**source,'columns':columns});continue
            # Keep balances, tax and totals distinct, including dollarless printed totals.
            amount=numeric(row[-1][4]);label=' '.join(w[4] for w in row[:-1]).lower().rstrip(':')
            if label in SUMMARIES and amount is not None:
                amounts.append({**source,'label':label,'value':amount,
                    'currency_symbol':'$' if '$' in row[-1][4] else None,'currency_confirmed':False})
                columns=None;continue
            if columns is None:continue
            cuts=[(a['bbox'][2]+b['bbox'][0])/2 for a,b in zip(columns,columns[1:])]
            cells={c['field']:[] for c in columns}
            for word in row:
                center=(word[0]+word[2])/2
                index=sum(center>cut for cut in cuts)
                cells[columns[index]['field']].append(word)
            values={k:' '.join(w[4] for w in cell) for k,cell in cells.items()}
            numbers={k:numeric(values[k]) for k in ('quantity','unit_rate','amount')}
            if not values['description'] or any(v is None for v in numbers.values()):
                unparsed.append({**source,'reason':'Table row is incomplete or cannot be assigned to explicit numeric columns'})
                continue
            with localcontext() as context:
                context.prec=max(28,len(numbers['quantity'])+len(numbers['unit_rate'])+4)
                expected=(Decimal(numbers['quantity'])*Decimal(numbers['unit_rate'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            candidates.append({**source,'description':values['description'],**numbers,
                'cell_sources':{k:{'text':values[k],'bbox':position(v) if v else None} for k,v in cells.items()},
                **explicit_unit(values.get('quantity_unit','')),'scope_ids':[],
                'currency_confirmed':False,'calculated_amount':format(expected,'f'),
                'arithmetic_matches':expected==Decimal(numbers['amount']),
                'header_bbox':headers[-1]['bbox'],'extraction_method':'native_word_columns'})
    return {'pricing_candidates':candidates,'labeled_amount_candidates':amounts,
            'table_headers':headers,'unparsed_table_rows':unparsed,
            'status':'unreviewed','purchase_authorized':False,
            'complete_document_pricing':False,
            'note':'Native table candidates only. Units, scope, currency, document completeness and current pricing need review.'}
