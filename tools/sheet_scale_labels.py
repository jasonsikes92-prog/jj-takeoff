"""Locate printed scale labels; labels alone do not calibrate measurements."""
import re
import statistics
from fractions import Fraction


def scale_labels(page,view_bounds_pt=None):
    labels=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            if view_bounds_pt is not None:
                x0,y0,x1,y1=line['bbox'];a,b,c,d=view_bounds_pt
                if not (a<=x0<x1<=c and b<=y0<y1<=d):continue
            text=''.join(s['text'] for s in line['spans']).strip()
            match=re.fullmatch(r'(?:SCALE\s*:?\s*)?(\d+(?:/\d+|\.\d+)?)\s*(?:"|in(?:ch(?:es)?)?\.?)\s*=\s*(\d+(?:\.\d+)?)\s*(?:\'|ft\.?|feet|foot)(?:\s*-?\s*0\s*")?',text,re.I)
            if match:
                try: inches=float(Fraction(match[1]));feet=float(match[2])
                except (ValueError,ZeroDivisionError):continue
                if inches<=0 or feet<=0:continue
                labels.append({'text':text,'bbox_pt':list(line['bbox']),
                    'nominal_points_per_foot':72*inches/feet,'not_to_scale':False})
            elif re.search(r'\b(?:NO SCALE|NOT TO SCALE|N\.?T\.?S\.?)\b',text,re.I):
                labels.append({'text':text,'bbox_pt':list(line['bbox']),
                    'nominal_points_per_foot':None,'not_to_scale':True})
    numeric={round(l['nominal_points_per_foot'],6) for l in labels if not l['not_to_scale']}
    mixed=len(numeric)>1 or (bool(numeric) and any(l['not_to_scale'] for l in labels))
    return {'labels':labels,'mixed_view_scales':mixed,'calibrated':False}


def corroborate_dimension_scale(dimensions, printed):
    """Two measured axes plus a matching printed scale can support a candidate.

    Never use the label alone, resolve mixed views, or certify quantities here.
    All extracted dimension controls must agree with the single printed scale.
    """
    controls = dimensions['controls']
    numeric = {round(label['nominal_points_per_foot'], 6) for label in printed['labels']
               if not label['not_to_scale']}
    if (printed['mixed_view_scales'] or len(numeric) != 1 or
            any(label['not_to_scale'] for label in printed['labels']) or
            {control['axis'] for control in controls} != {'horizontal', 'vertical'}):
        return dimensions
    nominal = next(iter(numeric))
    if not all(abs(control['points_per_foot'] / nominal - 1) <= .005 for control in controls):
        return dimensions
    return {**dimensions, 'points_per_foot': statistics.median(c['points_per_foot'] for c in controls),
            'usable_candidate': True, 'agreeing_controls': len(controls),
            'method': 'two-axis dimension controls corroborated by printed scale',
            'printed_scale_evidence': printed['labels'], 'certified': False}
