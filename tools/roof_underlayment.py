"""Full-width underlayment course cuts on a calibrated pitched roof face."""
import math
from shapely.geometry import Polygon,box
from shapely.ops import unary_union


def feltbuster_courses(face, upslope_gradient):
    """Standard GAF FeltBuster layout; six-inch terminal allowance at each end.

    Uses 48-inch stock, 3-inch side laps above 4:12, and 22.5-inch exposure
    plus a full-width starting layer for 2:12 to below 4:12. No end splices
    within a course or reuse of diagonal offcuts; quantity estimate only.
    """
    scale=face['points_per_foot'];gx,gy=upslope_gradient
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (scale,gx,gy)) or scale<=0:
        raise ValueError('Finite positive calibration and gradient required')
    slope=math.hypot(gx,gy);factor=math.sqrt(1+slope*slope)
    if slope<2/12:raise ValueError('FeltBuster course basis requires at least 2:12 pitch')
    if not math.isclose(factor,face['surface_factor'],rel_tol=1e-8):
        raise ValueError('Roof face slope factor and upslope gradient disagree')
    ox,oy=face['points'][0]
    points=[((-(x-ox)*gy+(y-oy)*gx)/(slope*scale),
             ((x-ox)*gx+(y-oy)*gy)*factor/(slope*scale)) for x,y in face['points']]
    polygon=Polygon(points)
    if not polygon.is_valid or polygon.area<=0:raise ValueError('Valid roof face required')
    xmin,ymin,xmax,ymax=polygon.bounds;low=slope<4/12
    starts=[];y=ymin
    if low:starts.append(('starter',ymin))
    while y<ymax-1e-9:
        starts.append(('course',y))
        if not low and y+4>=ymax:break
        y+=22.5/12 if low else 45/12
    courses=[];coverage=[]
    for kind,y in starts:
        segment=polygon.intersection(box(xmin-1,y,xmax+1,y+4))
        if segment.area<=1e-10:continue
        left,_,right,_=segment.bounds
        cut_length=right-left+1
        if cut_length>250:raise ValueError('Course exceeds roll length; explicit end-splice layout needed')
        courses.append({'id':f"{face['id']}-{len(courses)+1:02}",'kind':kind,
            'start_upslope_ft':y-ymin,'cut_length_ft':cut_length,'width_ft':4,
            'terminal_allowance_ft':1,'left_ft':left-.5,'right_ft':right+.5})
        coverage.append(segment)
    uncovered=polygon.difference(unary_union(coverage)).area
    double_uncovered=None
    if low:
        doubles=[a.intersection(b) for i,a in enumerate(coverage) for b in coverage[i+1:]]
        double_uncovered=polygon.difference(unary_union(doubles)).area
    assert uncovered<1e-7 and (double_uncovered is None or double_uncovered<1e-7)
    return {'face_id':face['id'],'surface_sf':polygon.area,'pitch_rise_per_12':slope*12,
        'low_slope_double_coverage':low,'courses':courses,
        'cut_length_ft':math.fsum(c['cut_length_ft'] for c in courses),
        'uncut_stock_area_sf':math.fsum(c['cut_length_ft']*4 for c in courses),
        'uncovered_sf':uncovered,'less_than_double_coverage_sf':double_uncovered,
        'order_released':False}
