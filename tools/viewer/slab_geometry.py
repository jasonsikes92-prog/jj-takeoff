"""Mixed slab edges, physical concrete volumes and comparison-only tolerances."""
import math


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1]
                   for a,b in zip(points,points[1:]+points[:1])))/2


def offset_edges(points, offsets):
    """Intersect shifted orthogonal edges; positive offsets expand the polygon."""
    if len(points) != len(offsets) or len(points) < 4:
        raise ValueError('Provide one offset for every edge')
    if any(not math.isfinite(v) for p in points for v in p) or any(not math.isfinite(v) for v in offsets):
        raise ValueError('Coordinates and offsets must be finite')
    signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
    if signed <= 0:
        raise ValueError('Expected the source polygon in positive winding order')
    lines = []
    for a,b,d in zip(points,points[1:]+points[:1],offsets):
        dx,dy=b[0]-a[0],b[1]-a[1]
        if dx == 0 and dy != 0:
            lines.append(('x',a[0]+math.copysign(1,dy)*d))
        elif dy == 0 and dx != 0:
            lines.append(('y',a[1]-math.copysign(1,dx)*d))
        else:
            raise ValueError('Use alternating horizontal and vertical source edges')
    result=[]
    for previous,current in zip(lines[-1:]+lines[:-1],lines):
        if previous[0] == current[0]:
            raise ValueError('Merge consecutive collinear edges first')
        cross=dict([previous,current])
        result.append([cross['x'],cross['y']])
    return result


def horizontal_band_area(points):
    """Second area calculation by horizontal slices, in the input units squared."""
    levels=sorted({p[1] for p in points})
    total=0
    for low,high in zip(levels,levels[1:]):
        y=(low+high)/2
        hits=[]
        for a,b in zip(points,points[1:]+points[:1]):
            if min(a[1],b[1]) < y < max(a[1],b[1]):
                hits.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        hits.sort()
        if len(hits)%2:
            raise ValueError('The slice does not close')
        total += sum(b-a for a,b in zip(hits[::2],hits[1::2]))*(high-low)
    return total


def compare_area(measured, reference, tolerance_pct, same_basis):
    if any(not math.isfinite(v) for v in (measured,reference,tolerance_pct)) or min(measured,reference)<=0 or tolerance_pct<0:
        raise ValueError('Areas must be positive and tolerance nonnegative')
    difference=100*(measured-reference)/reference
    return {'difference_percent':difference,'tolerance_percent':tolerance_pct,
            'same_basis':same_basis,
            'within_tolerance':abs(difference)<=tolerance_pct if same_basis else None,
            'certifies_quantity':False}


def grade_beam_volume(eligible_wall_lf, slab_in, total_depth_in, bottom_width_in, waste_pct, side_angle_deg=90):
    """LF allowance with two sloped sides; total depth starts at slab top."""
    values=(eligible_wall_lf,slab_in,total_depth_in,bottom_width_in,waste_pct,side_angle_deg)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('Grade-beam length and dimensions must be finite numbers')
    if eligible_wall_lf<0 or min(slab_in,bottom_width_in)<=0 or total_depth_in<slab_in or waste_pct<0:
        raise ValueError('Grade-beam depth must include the slab; length and waste cannot be negative')
    if not 0<side_angle_deg<=90:
        raise ValueError('Grade-beam side angle must be above zero and at most 90 degrees')
    extra_in=total_depth_in-slab_in
    run_in=0 if side_angle_deg==90 else extra_in/math.tan(math.radians(side_angle_deg))
    top_width_in=bottom_width_in+2*run_in
    section_in2=(bottom_width_in+top_width_in)/2*extra_in
    extra_cy=eligible_wall_lf*section_in2/144/27
    return {'eligible_wall_lf':eligible_wall_lf,'additional_depth_inches':extra_in,
            'bottom_width_inches':bottom_width_in,'top_width_inches':top_width_in,
            'side_angle_degrees':side_angle_deg,'side_run_inches':run_in,
            'additional_section_square_inches':section_in2,
            'extra_beam_cy':extra_cy,'waste_cy':extra_cy*waste_pct/100,
            'with_waste_cy':extra_cy*(1+waste_pct/100),
            'basis':'LF allowance; trapezoidal section below slab; beam intersections and edge overlaps not deducted',
            'intersection_review_required':eligible_wall_lf>0 and extra_in>0,
            'certifies_quantity':False}


def roll_layout(points_ft, width_ft, length_ft, lap_inches):
    """Full-width strips covering the planar footprint; compare both directions."""
    from slab_review import validate_polygon
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (width_ft,length_ft,lap_inches)):
        raise ValueError('Roll width, length and overlap must be positive')
    lap=lap_inches/12
    if lap>=width_ft:raise ValueError('Overlap must be less than roll width')
    offset_edges(points_ft,[0]*len(points_ft))
    low=[min(p[k] for p in points_ft) for k in (0,1)]
    high=[max(p[k] for p in points_ft) for k in (0,1)]
    span=[high[k]-low[k] for k in (0,1)]
    validate_polygon([[p[k]-low[k] for k in (0,1)] for p in points_ft],span[0]+1,span[1]+1)
    candidates=[]
    for axis in (0,1):
        cross=1-axis;cut_length=span[axis]
        per_roll=math.floor(length_ft/cut_length+1e-9)
        if not per_roll:continue
        count=max(1,math.ceil((span[cross]-lap)/(width_ft-lap)-1e-9))
        if count>10000:raise ValueError('Too many strips for this bounded review')
        strips=[]
        for i in range(count):
            a=low.copy();b=high.copy()
            a[cross]=low[cross]+i*(width_ft-lap);b[cross]=a[cross]+width_ft
            strips.append({'id':i+1,'roll':i//per_roll+1,'bounds_ft':[a[0],a[1],b[0],b[1]],'cut_length_ft':cut_length})
        rolls=math.ceil(count/per_roll);cut_area=count*cut_length*width_ft
        lap_area=(count-1)*lap*cut_length;net=area(points_ft)
        candidates.append({'direction':'horizontal' if axis==0 else 'vertical','strips':strips,
            'strip_count':count,'roll_count':rolls,'roll_width_ft':width_ft,'roll_length_ft':length_ft,
            'lap_inches':lap_inches,'cut_length_ft':cut_length,'total_cut_length_ft':count*cut_length,
            'net_coverage_sf':net,'lap_area_sf':lap_area,'trim_area_sf':cut_area-lap_area-net,
            'cut_area_sf':cut_area,'purchased_area_sf':rolls*width_ft*length_ft,
            'uncut_remaining_sf':rolls*width_ft*length_ft-cut_area,
            'basis':'Planar footprint only. Full-width strips span the bounding rectangle, with the recorded side lap. Trim around slab jogs; trimmed width offcuts not reused. No end splices, turn-downs or vertical surfaces included.',
            'certifies_quantity':False})
    if not candidates:raise ValueError('Slab exceeds roll length in both directions; an end-splice layout is required')
    return min(candidates,key=lambda c:(c['roll_count'],c['cut_area_sf']))


def material_coverage_cells(points_ft, edge_roles, bearing_inches, thickened_inches):
    """Projected material cells outside the specified edge exclusions."""
    from slab_review import validate_polygon
    if len(edge_roles)!=len(points_ft) or any(r not in ('bearing','thickened') for r in edge_roles):
        raise ValueError('Classify every material boundary edge')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (bearing_inches,thickened_inches)):
        raise ValueError('Material edge exclusions must be nonnegative inches')
    offset_edges(points_ft,[0]*len(points_ft))
    low=[min(p[k] for p in points_ft) for k in (0,1)]
    high=[max(p[k] for p in points_ft) for k in (0,1)]
    validate_polygon([[p[k]-low[k] for k in (0,1)] for p in points_ft],high[0]-low[0]+1,high[1]-low[1]+1)
    rectangles=[];normals=[];widths=[]
    for a,b,role in zip(points_ft,points_ft[1:]+points_ft[:1],edge_roles):
        length=math.dist(a,b);width=(bearing_inches if role=='bearing' else thickened_inches)/12
        nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
        normals.append((nx,ny));widths.append(width)
        corners=[a,b,[a[0]+nx*width,a[1]+ny*width],[b[0]+nx*width,b[1]+ny*width]]
        rectangles.append([min(c[0] for c in corners),min(c[1] for c in corners),max(c[0] for c in corners),max(c[1] for c in corners)])
    for i,b in enumerate(points_ft):
        a,c=points_ft[i-1],points_ft[(i+1)%len(points_ft)]
        if (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])<0:
            end=[b[k]+normals[i-1][k]*widths[i-1]+normals[i][k]*widths[i] for k in (0,1)]
            rectangles.append([min(b[0],end[0]),min(b[1],end[1]),max(b[0],end[0]),max(b[1],end[1])])
    xs=sorted({p[0] for p in points_ft}|{v for r in rectangles for v in (r[0],r[2]) if low[0]<v<high[0]})
    ys=sorted({p[1] for p in points_ft}|{v for r in rectangles for v in (r[1],r[3]) if low[1]<v<high[1]})
    cells=[]
    for y0,y1 in zip(ys,ys[1:]):
        y=(y0+y1)/2
        hits=sorted(a[0] for a,b in zip(points_ft,points_ft[1:]+points_ft[:1]) if min(a[1],b[1])<y<max(a[1],b[1]))
        for x0,x1 in zip(xs,xs[1:]):
            x=(x0+x1)/2
            inside=any(a<x<b for a,b in zip(hits[::2],hits[1::2]))
            if inside and not any(a<x<c and b<y<d for a,b,c,d in rectangles):cells.append([x0,y0,x1,y1])
    if not cells:raise ValueError('No flat material coverage remains after edge exclusions')
    bounds=[min(r[0] for r in cells),min(r[1] for r in cells),max(r[2] for r in cells),max(r[3] for r in cells)]
    net=sum((c-a)*(d-b) for a,b,c,d in cells)
    return {'rectangles_ft':cells,'bounds_ft':bounds,'net_sf':net,'excluded_sf':area(points_ft)-net,
        'bearing_exclusion_inches':bearing_inches,'thickened_exclusion_inches':thickened_inches,
        'basis':'Projected area with separate-wall bearing and specified thickened-edge bands excluded.',
        'certifies_quantity':False}


def rebar_grid(points_ft, spacing_inches, setback_inches, lap_inches, stock_length_ft, *, balance_far_edge=False):
    """Axis-aligned estimating layout; clipped runs and a feasible offcut schedule."""
    from slab_review import validate_polygon
    values=(*spacing_inches,setback_inches,lap_inches,stock_length_ft)
    if len(spacing_inches)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):
        raise ValueError('Grid spacing, setback, lap and stock length must be positive')
    lap=lap_inches/12
    if lap>=stock_length_ft:raise ValueError('Lap must be shorter than a stock bar')
    inset=offset_edges(points_ft,[-setback_inches/12]*len(points_ft))
    for i,a in enumerate(inset):
        b=inset[(i+1)%len(inset)];p,q=points_ft[i],points_ft[(i+1)%len(inset)]
        if sum((b[k]-a[k])*(q[k]-p[k]) for k in (0,1))<=0:
            raise ValueError('Grid setback collapses an edge; review the layout')
    low=[min(p[k] for p in inset) for k in (0,1)]
    high=[max(p[k] for p in inset) for k in (0,1)]
    validate_polygon([[p[k]-low[k] for k in (0,1)] for p in inset],high[0]-low[0]+1,high[1]-low[1]+1)
    segments=[]
    for axis in (0,1):
        cross=1-axis;step=spacing_inches[cross]/12
        count=math.floor((high[cross]-low[cross])/step+1e-9)
        if count>10000:raise ValueError('Too many grid runs for this bounded review')
        positions=[min(high[cross],low[cross]+i*step) for i in range(count+1)]
        if high[cross]-positions[-1]>1e-9:
            positions.append(high[cross])
            # Preserve both edge setbacks and the run count without a tiny last gap.
            if balance_far_edge and len(positions)>=3:
                positions[-2]=(positions[-3]+positions[-1])/2
        for position in positions:
            ranges=[]
            # Include a run on the inset boundary, including either side of a notch.
            for probe in (math.nextafter(position,-math.inf),math.nextafter(position,math.inf)):
                hits=sorted(a[axis] for a,b in zip(inset,inset[1:]+inset[:1])
                    if min(a[cross],b[cross])<probe<max(a[cross],b[cross]))
                if len(hits)%2:raise ValueError('Grid slice does not close')
                ranges.extend(zip(hits[::2],hits[1::2]))
            merged=[]
            for start,end in sorted(ranges):
                if merged and start<=merged[-1][1]:merged[-1][1]=max(end,merged[-1][1])
                else:merged.append([start,end])
            for start,end in merged:
                a=[position,position];b=a.copy();a[axis]=start;b[axis]=end
                length=end-start
                pieces=max(1,math.ceil((length-lap)/(stock_length_ft-lap)-1e-9))
                cuts=[stock_length_ft]*(pieces-1)+[length-(pieces-1)*(stock_length_ft-lap)]
                segments.append({'id':len(segments)+1,'direction':'horizontal' if axis==0 else 'vertical',
                    'start_ft':a,'end_ft':b,'net_lf':length,'splice_count':pieces-1,'cuts_ft':cuts})
    if not segments:raise ValueError('No grid fits inside the slab')
    stocks=[]
    cuts=[{'run_id':s['id'],'piece':i+1,'length_ft':length} for s in segments for i,length in enumerate(s['cuts_ft'])]
    for cut in sorted(cuts,key=lambda c:-c['length_ft']):
        stock=next((s for s in stocks if s['remaining_ft']+1e-9>=cut['length_ft']),None)
        if stock is None:
            stock={'id':len(stocks)+1,'cuts':[],'remaining_ft':stock_length_ft};stocks.append(stock)
        stock['cuts'].append(cut);stock['remaining_ft']-=cut['length_ft']
    net=sum(s['net_lf'] for s in segments);splices=sum(s['splice_count'] for s in segments)
    return {'segments':segments,'stocks':stocks,'run_count':len(segments),'net_lf':net,
        'splice_count':splices,'lap_lf':splices*lap,'cut_lf':net+splices*lap,
        'stock_length_ft':stock_length_ft,'stock_count':len(stocks),'purchase_lf':len(stocks)*stock_length_ft,
        'offcut_lf':len(stocks)*stock_length_ft-net-splices*lap,
        'setback_inches':setback_inches,'lap_inches':lap_inches,'spacing_inches':spacing_inches,
        'layout_basis':('Parallel to drawing axes; start at top/left inset; maximum stated spacing; add far inset row; clip at every jog. Setback measured to estimating lines/endpoints.'
                        + (' Balance the final two spaces when the far inset leaves a partial bay.' if balance_far_edge else '')),
        'cutting_basis':'Full-length pieces first per run; reuse remaining cuts in descending length order. Feasible schedule, not guaranteed minimum; cutting loss not added.',
        'certifies_quantity':False}


def concrete_volume(points_ft, edge_indexes, slab_in, depth_in, bottom_in, vertical_in, angle_deg, waste_pct):
    """Integrate the extra edge volume below the slab, with mitered plan corners."""
    from slab_review import validate_polygon
    values=(slab_in,depth_in,bottom_in,vertical_in,angle_deg,waste_pct)
    if any(not math.isfinite(v) for v in values) or min(slab_in,bottom_in)<=0 or vertical_in<0 or waste_pct<0:
        raise ValueError('Invalid concrete dimensions or waste')
    rise_in=depth_in-slab_in-vertical_in
    if rise_in<0 or not 0<angle_deg<90:
        raise ValueError('The haunch must fit below the slab')
    if not edge_indexes or any(type(i) is not int or not 0<=i<len(points_ft) for i in edge_indexes):
        raise ValueError('Identify the eligible thickened edges')
    run_in=rise_in/math.tan(math.radians(angle_deg))
    bottom=bottom_in/12
    top=(bottom_in+run_in)/12
    base_area=area(points_ft)
    offset_edges(points_ft,[0]*len(points_ft))
    min_x=min(p[0] for p in points_ft);min_y=min(p[1] for p in points_ft)
    shifted=[[x-min_x,y-min_y] for x,y in points_ft]
    validate_polygon(shifted,max(p[0] for p in shifted)+1,max(p[1] for p in shifted)+1)

    def band(width):
        rectangles=[]
        normals={}
        for i in edge_indexes:
            a,b=points_ft[i],points_ft[(i+1)%len(points_ft)]
            length=math.dist(a,b)
            nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
            normals[i]=(nx,ny)
            corners=[a,b,[a[0]+nx*width,a[1]+ny*width],[b[0]+nx*width,b[1]+ny*width]]
            rectangles.append([min(c[0] for c in corners),min(c[1] for c in corners),max(c[0] for c in corners),max(c[1] for c in corners)])
        # Fill mitered inside corners; outside-corner rectangles already overlap.
        for i in edge_indexes:
            previous=(i-1)%len(points_ft)
            if previous not in normals:continue
            a,b,c=points_ft[previous],points_ft[i],points_ft[(i+1)%len(points_ft)]
            if (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])<0:
                nx=normals[previous][0]+normals[i][0]
                ny=normals[previous][1]+normals[i][1]
                rectangles.append([min(b[0],b[0]+nx*width),min(b[1],b[1]+ny*width),max(b[0],b[0]+nx*width),max(b[1],b[1]+ny*width)])
        levels=sorted({p[1] for p in points_ft}|{r[k] for r in rectangles for k in (1,3)})
        result=0
        for low,high in zip(levels,levels[1:]):
            y=(low+high)/2
            hits=sorted(a[0] for a,b in zip(points_ft,points_ft[1:]+points_ft[:1]) if min(a[1],b[1])<y<max(a[1],b[1]))
            ranges=sorted((x0,x1) for x0,y0,x1,y1 in rectangles if y0<y<y1)
            union=[]
            for start,end in ranges:
                if union and start<=union[-1][1]:union[-1][1]=max(end,union[-1][1])
                else:union.append([start,end])
            result+=sum(max(0,min(b,d)-max(a,c)) for a,b in zip(hits[::2],hits[1::2]) for c,d in union)*(high-low)
        if not 0<result<base_area:
            raise ValueError('Haunch must remain within the slab footprint')
        return result

    a0,am,a1=[band(w) for w in (bottom,(bottom+top)/2,top)]
    def integrate(a,b,fa,fm,fb,whole,epsilon=1e-7,depth=12):
        middle=(a+b)/2
        fl=band(bottom+(top-bottom)*(a+middle)/2)
        fr=band(bottom+(top-bottom)*(middle+b)/2)
        left=(middle-a)*(fa+4*fl+fm)/6
        right=(b-middle)*(fm+4*fr+fb)/6
        delta=left+right-whole
        if abs(delta)<=15*epsilon:return left+right+delta/15
        if depth==0:raise ValueError('Volume integration did not converge')
        return integrate(a,middle,fa,fl,fm,left,epsilon/2,depth-1)+integrate(middle,b,fm,fr,fb,right,epsilon/2,depth-1)
    extra_ft3=vertical_in/12*a0+rise_in/12*integrate(0,1,a0,am,a1,(a0+4*am+a1)/6)
    check_ft3=vertical_in/12*a0+rise_in/12*sum(band(bottom+(top-bottom)*(i+.5)/400) for i in range(400))/400
    if abs(extra_ft3-check_ft3)>0.0001:
        raise ValueError('Independent volume integration did not agree')
    slab_cy=base_area*slab_in/12/27
    extra_cy=extra_ft3/27
    return {'slab_cy':slab_cy,'extra_edge_cy':extra_cy,'net_cy':slab_cy+extra_cy,
            'waste_cy':(slab_cy+extra_cy)*waste_pct/100,
            'with_waste_cy':(slab_cy+extra_cy)*(1+waste_pct/100),
            'haunch_rise_inches':rise_in,'haunch_run_inches':run_in,
            'top_width_inches':bottom_in+run_in,'bottom_band_sf':a0,'top_band_sf':a1,
            'independent_extra_cy':check_ft3/27,'corner_model':'union of inward edge strips and miter joins, clipped to footprint',
            'certifies_quantity':False}
