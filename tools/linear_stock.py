"""Auditable lapped cut lists and feasible whole-stock purchases."""
import math


def lapped_cuts(runs, maximum_piece_ft, lap_ft, end_allowance_ft=0):
    """Split each run; allowance is total per run, lap is per internal joint."""
    for value in (maximum_piece_ft,lap_ft,end_allowance_ft):
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Finite dimensions required')
    if not 0<=lap_ft<maximum_piece_ft or end_allowance_ft<0:
        raise ValueError('Invalid stock, lap or allowance')
    cuts=[];details=[];seen=set()
    for run in runs:
        identity=run['id'];length=run['length_ft']
        if not identity or identity in seen:raise ValueError('Unique run IDs required')
        seen.add(identity)
        if type(length) not in (int,float) or not math.isfinite(length) or length<0:
            raise ValueError('Nonnegative finite run length required')
        if length==0:
            details.append({'id':identity,'net_length_ft':0,'cuts_ft':[],'joint_count':0})
            continue
        required=length+end_allowance_ft
        count=max(1,math.ceil((required-lap_ft)/(maximum_piece_ft-lap_ft)))
        pieces=[maximum_piece_ft]*(count-1)+[required+(count-1)*lap_ft-(count-1)*maximum_piece_ft]
        assert all(0<p<=maximum_piece_ft+1e-9 for p in pieces)
        cuts.extend({'run_id':identity,'piece':i+1,'length_ft':p} for i,p in enumerate(pieces))
        details.append({'id':identity,'net_length_ft':length,'end_allowance_ft':end_allowance_ft,
                        'cuts_ft':pieces,'joint_count':count-1})
    return {'runs':details,'cuts':cuts,'cut_length_ft':math.fsum(c['length_ft'] for c in cuts)}


def pack_sawn_cuts(pieces, kerf_inches=.125):
    """Feasible best-fit cuts within exact SKUs; never splice an oversized piece.

    Kerf is capped at the unused factory-end sliver. End trimming, defects and
    structural applicability are caller-owned assumptions, not inferred here.
    """
    if type(kerf_inches) not in (int, float) or not math.isfinite(kerf_inches) or kerf_inches < 0:
        raise ValueError('Nonnegative finite saw kerf required')
    seen = set(); stock_by_sku = {}
    for piece in pieces:
        identity, sku = piece['id'], piece['sku']
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError('Unique cut-piece IDs required')
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError('Exact stock SKU required')
        seen.add(identity)
        length, cut = piece['stock_length_ft'], piece['cut_inches']
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (length, cut)):
            raise ValueError('Positive finite cut and stock lengths required')
        if cut > length * 12:
            raise ValueError('Cut does not fit stock: ' + identity)
        if sku in stock_by_sku and stock_by_sku[sku] != length:
            raise ValueError('One stock length required per SKU')
        stock_by_sku[sku] = length
    boards = []
    for piece in sorted(pieces, key=lambda p: (-p['cut_inches'], p['id'])):
        candidates = [b for b in boards if b['sku'] == piece['sku'] and b['remaining_inches'] >= piece['cut_inches']]
        board = min(candidates, key=lambda b: b['remaining_inches']) if candidates else None
        if board is None:
            board = {'id':f'B{len(boards)+1:03}', 'sku':piece['sku'], 'length_ft':piece['stock_length_ft'],
                     'remaining_inches':piece['stock_length_ft']*12, 'cuts':[]}
            boards.append(board)
        consumed = piece['cut_inches'] + min(kerf_inches, board['remaining_inches']-piece['cut_inches'])
        board['cuts'].append({'piece_id':piece['id'], 'cut_inches':piece['cut_inches'], 'consumed_inches':consumed})
        board['remaining_inches'] -= consumed
    return boards


def pack_cuts(cuts, stock_length_ft):
    """Best-fit decreasing; returns a feasible cutting plan, not an optimum claim.

    For sheared flashing/roll goods: no saw kerf. All cuts must share one product.
    """
    if type(stock_length_ft) not in (int,float) or not math.isfinite(stock_length_ft) or stock_length_ft<=0:
        raise ValueError('Positive finite stock length required')
    if any(type(c['length_ft']) not in (int,float) or not math.isfinite(c['length_ft'])
           or not 0<c['length_ft']<=stock_length_ft for c in cuts):
        raise ValueError('Cut does not fit stock')
    stocks=[]
    for cut in sorted(cuts,key=lambda c:(-c['length_ft'],c['run_id'],c['piece'])):
        fits=[s for s in stocks if s['remaining_ft']+1e-9>=cut['length_ft']]
        target=min(fits,key=lambda s:s['remaining_ft']) if fits else None
        if target is None:
            target={'stock_number':len(stocks)+1,'cuts':[],'remaining_ft':stock_length_ft}
            stocks.append(target)
        target['cuts'].append(dict(cut));target['remaining_ft']-=cut['length_ft']
    return {'stock_length_ft':stock_length_ft,'quantity':len(stocks),'stocks':stocks,
            'purchased_length_ft':len(stocks)*stock_length_ft,
            'unused_length_ft':math.fsum(s['remaining_ft'] for s in stocks),
            'optimality_proven':False,'order_released':False}
