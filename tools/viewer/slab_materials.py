"""Whole purchase units and separate slab material/support allowances."""
import math
from decimal import Decimal, ROUND_CEILING
from slab_geometry import material_coverage_cells, roll_layout


def whole_units(quantity, size=1):
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (quantity,size)) or quantity<0 or size<=0:
        raise ValueError('Purchase quantity must be nonnegative and package size positive')
    return int((Decimal(str(quantity))/Decimal(str(size))).to_integral_value(rounding=ROUND_CEILING))


def gravel_truckloads(cubic_yards, delivery):
    density=delivery['tons_per_cy'];capacity=delivery['tons_per_load']
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (density,capacity)):
        raise ValueError('Stone density and truck capacity must be positive')
    tons=float(Decimal(str(cubic_yards))*Decimal(str(density)))
    loads=whole_units(tons,capacity)
    return {'required_tons':tons,'truckloads':loads,'purchased_tons':loads*capacity,
        'cy_per_load':capacity/density,'purchased_equivalent_cy':loads*capacity/density,
        'tons_per_cy':density,'tons_per_load':capacity}


def substrate_coverage(points, profile, concrete):
    specs=profile['material_specs'];roles=profile['edge_roles']
    if specs['substrate_extent']!='footer_haunch_junction':raise ValueError('Unknown substrate termination')
    bearing=specs['bearing_overlap_inches']
    flat=material_coverage_cells(points,roles,bearing,concrete['top_width_inches'])
    projected=material_coverage_cells(points,roles,bearing,profile['exterior']['bottom_width_inches'])
    slope_plan=projected['net_sf']-flat['net_sf']
    angle=math.radians(profile['exterior']['angle_degrees'])
    slope_surface=slope_plan/math.cos(angle)
    total=flat['net_sf']+slope_surface
    result={'flat':flat,'projected':projected,'haunch_plan_sf':slope_plan,'haunch_surface_sf':slope_surface,
        'surface_sf':total,'stopping_depth_below_slab_top_inches':profile['exterior']['total_depth_inches']-profile['exterior']['vertical_inches_above_bottom'],
        'gravel_volume_basis':'Surface area times 4-inch normal thickness; in-place estimating allowance. Compaction, delivery conversion and corner bedding adjustments require review.',
        'certifies_quantity':False}
    if specs.get('gravel_thickness_direction')=='perpendicular':
        result['gravel_in_place_cy']=total*specs['gravel_depth_inches']/12/27
    elif specs.get('gravel_thickness_direction')=='vertical':
        result['gravel_in_place_cy']=projected['net_sf']*specs['gravel_depth_inches']/12/27
    return result


def plastic_layout(coverage, specs, concrete):
    # A conservative rectangular sheet development reserves the full haunch
    # length on all four sides, including unused sides that become trim.
    x0,y0,x1,y1=coverage['flat']['bounds_ft']
    extension=math.hypot(concrete['haunch_run_inches'],concrete['haunch_rise_inches'])/12
    rectangle=[[x0-extension,y0-extension],[x1+extension,y0-extension],[x1+extension,y1+extension],[x0-extension,y1+extension]]
    product=specs['vapor_product']
    layout=roll_layout(rectangle,product['width_ft'],product['length_ft'],specs['vapor_lap_inches'])
    layout['net_coverage_sf']=coverage['surface_sf']
    layout['trim_area_sf']=layout['cut_area_sf']-layout['lap_area_sf']-coverage['surface_sf']
    if layout['trim_area_sf']<0:raise ValueError('Plastic cutting layout does not cover developed haunch surface')
    layout['coverage_rectangles_ft']=coverage['projected']['rectangles_ft']
    layout['basis']='Conservative developed rectangle: flat-area bounds plus full haunch slope length on every side. Includes side laps and trim; unused side extensions remain trim. Green drawing shows projected coverage, not unfolded cutting seams.'
    return layout


def inside_cells(point, cells):
    x,y=point
    return any(a-1e-9<=x<=c+1e-9 and b-1e-9<=y<=d+1e-9 for a,b,c,d in cells)


def grid_crossings(grid):
    points=set()
    for h in (s for s in grid['segments'] if s['direction']=='horizontal'):
        for v in (s for s in grid['segments'] if s['direction']=='vertical'):
            x,y=v['start_ft'][0],h['start_ft'][1]
            if h['start_ft'][0]-1e-9<=x<=h['end_ft'][0]+1e-9 and v['start_ft'][1]-1e-9<=y<=v['end_ft'][1]+1e-9:
                points.add((x,y))
    return [list(p) for p in sorted(points)]


def footer_stock_allowance(points, profile):
    """Budget each full boundary run separately; do not claim a fabrication layout."""
    specs=profile['material_specs'];roles=profile['edge_roles']
    if specs.get('footer_end_connection')!='lap_to_projecting_wall_rebar':
        raise ValueError('Footer stock allowance needs the recorded wall-bar connection')
    if specs.get('footer_stock_basis')!='gross_boundary_budget':
        raise ValueError('Unknown footer stock allowance basis')
    if specs.get('rebar_lap_rule')!='irc2024_no4_grade60' or specs.get('rebar_grade')!=60 or specs.get('footer_rebar_size')!='#4':
        raise ValueError('Wall-bar allowance requires the recorded #4 Grade 60 specification')
    starts=[i for i,r in enumerate(roles) if r=='thickened' and roles[i-1]!='thickened']
    ends=[(i+1)%len(roles) for i,r in enumerate(roles) if r=='thickened' and roles[(i+1)%len(roles)]!='thickened']
    if len(starts)!=1 or len(ends)!=1:
        raise ValueError('Wall-bar allowance requires one open chain of thickened edges')
    runs=specs['footer_rebar_runs'];stock=specs['rebar_stock_length_ft'];lap_inches=specs['footer_rebar_lap_inches']
    if type(runs) is not int or runs<=0 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (stock,lap_inches)):
        raise ValueError('Footer runs, stock length and lap must be positive')
    if lap_inches<30:raise ValueError('Wall-bar allowance requires at least 30-inch laps')
    lap=lap_inches/12
    if lap>=stock:raise ValueError('Footer lap must be shorter than stock length')
    length=sum(math.dist(points[i],points[(i+1)%len(points)]) for i,r in enumerate(roles) if r=='thickened')
    if length<=2*lap:raise ValueError('Wall lap zones consume this short footer; review its bar layout')
    pieces=max(1,whole_units(max(0,length-lap),stock-lap));splices=runs*(pieces-1)
    return {'budget_sticks':runs*pieces,'sticks_per_run':pieces,'internal_splice_count':splices,
        'internal_lap_lf':splices*lap,'budget_length_lf':runs*length+splices*lap,
        'budget_purchase_lf':runs*pieces*stock,'wall_connection_count':runs*2,
        'wall_lap_zone_lf':runs*2*lap,'added_wall_lap_lf':0,
        'wall_junction_points_ft':[points[starts[0]],points[ends[0]]],
        'starter_material_scope':'Projecting bars belong to the separate poured-wall scope; their embedded length is not quantified or purchased here.',
        'basis':'Budget from full measured boundary lengths and internal laps; round each run to whole sticks without sharing offcuts. Wall overlap lies inside the measured run, so do not add it again. No offset/bend deduction taken. Final routing, bend cuts and available starter projection still need verification.',
        'fabrication_schedule_verified':False,'certifies_quantity':False}


def material_allowances(points, profile, result):
    specs=profile.get('material_specs',{});items={};chairs={}
    def item(name,quantity,unit,measured,measured_unit,basis):
        return {'name':name,'quantity':quantity,'unit':unit,'measured_quantity':measured,'measured_unit':measured_unit,'quantity_status':basis}
    c=result['concrete']
    items['concrete']=item('Concrete',whole_units(c['with_waste_cy']),'CY',c['with_waste_cy'],'CY','round up after concrete waste, applied once')
    for name,layout in result.get('roll_layouts',{}).items():
        items[name]=item('Plastic' if name=='plastic' else 'Wire mesh',layout['roll_count'],'box' if name=='plastic' else 'roll',layout['net_coverage_sf'],'SF','whole packages from feasible strip cutting layout, including laps and trim')
    coverage=result.get('substrate_coverage')
    if coverage and 'gravel_in_place_cy' in coverage:
        q=coverage['gravel_in_place_cy']
        items['gravel']=item('Gravel',whole_units(q),'CY',q,'CY','rounded in-place allowance; compaction and delivered conversion pending')
        if profile.get('gravel_delivery'):
            delivery=gravel_truckloads(q,profile['gravel_delivery']);result['gravel_delivery']=delivery
            items['gravel'].update(name='#57 stone',quantity=delivery['truckloads'],unit='truckload',
                quantity_status=f"{delivery['required_tons']:.3f} tons estimated at {delivery['tons_per_cy']:g} tons/CY; round once to full {delivery['tons_per_load']:g}-ton trucks; quarry density and placement allowance remain estimating assumptions")
    grid=result.get('rebar_grid')
    if grid:
        items['grid']=item('Additional #4 rebar grid',grid['stock_count'],'stick',grid['cut_lf'],'LF','20-foot stock from cutting schedule, including recorded laps; reinforcement review and template mapping pending')
        if specs.get('rebar_lap_rule'):
            items['grid']['quantity_status']=f"#4 Grade {specs['rebar_grade']}, {specs['rebar_grid_lap_inches']:g}-inch laps; whole 20-foot sticks from cutting schedule; structural applicability and template mapping pending"
    elif specs.get('rebar_grid_included') is True:
        items['grid']=item('Additional #4 rebar grid',None,'stick',None,'LF','included scope; grid dimensions and cutting schedule required')
    rules=profile.get('support_rules',{})
    flat=coverage['flat']['rectangles_ft'] if coverage else None
    edge_methods=specs.get('deep_edge_support',{})
    if rules.get('mesh'):
        rule=rules['mesh'];spacing=rule['spacing_inches']/12
        low=[min(p[k] for p in points) for k in (0,1)];high=[max(p[k] for p in points) for k in (0,1)]
        cells=material_coverage_cells(points,profile['edge_roles'],0,0)['rectangles_ft']
        positions=[]
        # One support per <=24-inch cell; keep each point in its slab intersection.
        for i in range(whole_units(high[0]-low[0],spacing)):
            for j in range(whole_units(high[1]-low[1],spacing)):
                x0=low[0]+i*spacing;y0=low[1]+j*spacing
                intersections=[(max(a,x0),max(b,y0),min(c,x0+spacing),min(d,y0+spacing)) for a,b,c,d in cells]
                intersections=[r for r in intersections if r[2]>r[0] and r[3]>r[1]]
                if intersections:
                    a,b,c,d=max(intersections,key=lambda r:(r[2]-r[0])*(r[3]-r[1]))
                    positions.append([(a+c)/2,(b+d)/2])
        chairs['mesh']={'positions_ft':positions,'basis':'One support per occupied 24-inch plan cell; final positions follow actual mesh crossings.'}
    if grid and rules.get('grid'):
        chairs['grid']={'positions_ft':grid_crossings(grid),'basis':'One support at every actual rebar crossing, per manufacturer.'}
    for name,layout in chairs.items():
        rule=rules[name];positions=layout['positions_ft']
        standard=[p for p in positions if flat and inside_cells(p,flat)]
        layout.update(count=len(positions),standard_height_count=len(standard),special_height_count=len(positions)-len(standard),pack_size=rule['pack_size'],model=rule['model'],spacing_source=rule['source'],
            total_pack_equivalent=whole_units(len(positions),rule['pack_size']),standard_packs=whole_units(len(standard),rule['pack_size']))
        items[name+'_chairs']=item(name.capitalize()+' chairs for flat slab',layout['standard_packs'],'box',len(standard),'each','standard height supports over flat substrate only; edge supports listed separately for height/placement review')
        if edge_methods.get(name)=='mesh_spans_slope':
            if not flat:raise ValueError('Mesh span rule requires resolved flat-substrate coverage')
            spanned=[p for p in positions if not inside_cells(p,flat)]
            layout.update(candidate_positions_ft=positions,positions_ft=standard,count=len(standard),
                spanned_edge_positions_ft=spanned,spanned_edge_candidate_count=len(spanned),special_height_count=0,
                total_pack_equivalent=layout['standard_packs'],edge_support_method='mesh_spans_slope',
                placement_verified=False,basis='Flat-substrate mesh chairs follow the 24-inch estimating cells. Jason confirmed the mesh itself spans the slope; no separate tall mesh chairs are included. Final placement and elevation are unverified.')
            items[name+'_chairs']['quantity_status']='flat-substrate chairs only; mesh itself spans the slope per Jason; no extra tall mesh chairs included'
        elif edge_methods.get(name)=='chairs':
            layout.update(edge_support_method='chairs',placement_verified=False)
            height=specs.get('grid_edge_chair_height_inches') if name=='grid' else None
            if height is not None:
                layout['edge_chair_height_inches']=height
                edge_rule=rules.get('grid_edge')
                if edge_rule:
                    if edge_rule['height_inches']!=height:raise ValueError('Edge chair product height differs from confirmed height')
                    pack=edge_rule['pack_size']
                    if type(pack) is not int or pack<=0:raise ValueError('Edge chair pack size must be a positive whole number')
                    count=layout['special_height_count'];packs=whole_units(count,pack)
                    layout.update(edge_packs=packs,edge_pack_size=pack,edge_model=edge_rule['model'],edge_purchase_unit='bucket')
                    items['grid_edge_chairs']=item(f'{height:g}-inch rebar chairs at thickened edges (budget allowance)',
                        packs,'bucket',count,'each','one chair per counted edge crossing; whole buckets; support placement, bearing and steel elevation unverified')
    if specs.get('footer_rebar_runs'):
        runs=specs['footer_rebar_runs'];net=result['thickened_edge_lf']*runs
        result['footer_rebar']={'runs':runs,'bar_size':specs['footer_rebar_size'],'measured_lf':net,'footing_lf':result['thickened_edge_lf'],
            'stock_length_ft':specs['rebar_stock_length_ft'],'minimum_sticks_before_laps':whole_units(net,specs['rebar_stock_length_ft']),
            'purchase_sticks':None,'basis':'Two runs along measured exposed thickened edges. Separate poured-wall footings excluded. Bar offsets, corner bends, anchorage and footer lap schedule remain required.'}
        items['footer_rebar']=item('Footer '+specs['footer_rebar_size']+' rebar',None,'stick',net,'LF','two runs measured; final stick count awaits lap, bend and anchorage schedule')
        if specs.get('rebar_lap_rule'):
            result['footer_rebar'].update(lap_inches=specs['footer_rebar_lap_inches'],steel_grade=specs['rebar_grade'],
                lap_rule=specs['rebar_lap_rule'],basis='Two runs along exposed thickened edges with the revised lap specification. Corner continuity, bar offsets and end anchorage require a project detail before the cut schedule can be released.')
            items['footer_rebar']['quantity_status']=f"{specs['footer_rebar_lap_inches']:g}-inch laps specified; final stick count awaits corner, offset and anchorage schedule"
        if specs.get('footer_end_connection'):
            allowance=footer_stock_allowance(points,profile)
            result['footer_rebar'].update(allowance,end_connection=specs['footer_end_connection'])
            items['footer_rebar'].update(name='Footer #4 rebar (budget allowance)',quantity=allowance['budget_sticks'],
                quantity_status=f"Budget allowance: {allowance['sticks_per_run']} whole sticks per run with {specs['footer_rebar_lap_inches']:g}-inch internal laps; wall starters counted in wall scope. Final bend/cut layout and starter projection unverified.")
        if rules.get('footer'):
            rule=rules['footer'];count=0
            for i,role in enumerate(profile['edge_roles']):
                if role=='thickened':count+=whole_units(math.dist(points[i],points[(i+1)%len(points)]),rule['spacing_inches']/12)+1
            chairs['footer']={'count':count,'pack_size':rule['pack_size'],'standard_packs':whole_units(count,rule['pack_size']),
                'model':rule['model'],'basis':'At most 4 feet along each thickened-edge segment plus both segment ends; shared corners conservatively counted twice. One stand supports both bars.',
                'spacing_source':rule['source']}
            items['footer_chairs']=item('Two-bar footer stands',chairs['footer']['standard_packs'],'box',count,'each',chairs['footer']['basis'])
    return items,chairs
