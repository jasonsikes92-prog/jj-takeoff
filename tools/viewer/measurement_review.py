"""Serve the source-bound measurement editor on loopback only."""
import argparse
import hashlib
import http.server
import json
import sys
from datetime import date
from pathlib import Path
import fitz
from measurement_store import MeasurementStore,EditConflict,calculate,encode
from measurement_quantities import rollup
from measurement_estimate import template_draft,price_draft
from measurement_scope_reviews import ScopeReviews
from estimate_readiness import readiness
from estimate_summary import review_summary
from estimate_export_snapshot import export_snapshot
from saved_trade_snapshots import import_saved_trades
from linked_quantity_reviews import import_linked_quantities
from scope_applicability import apply_applicability
from framing_component_review import import_components
from kit_purchase_review import import_kit_purchases
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from package_pricing import price_packages
from wall_run_candidates import from_state as wall_runs
from wall_classification_review import read_review as wall_classification
from wall_alignment_breaks import read_review as wall_alignment
from wall_gap_labels import from_plan_state as wall_gap_labels
from opening_header_review import from_folder as opening_headers
from opening_schedule import from_folder as opening_schedule
from opening_quantity_review import import_quantities as import_opening_quantities
from opening_bid_scope import from_folder as opening_bid_scope
from wall_enclosure_candidates import from_folder as wall_enclosures
from enclosure_quantity_review import import_quantities as import_enclosure_quantities
from room_region_candidates import from_folder as room_regions
from drywall_bid_scope import from_folder as drywall_bid_scope
from roof_panel_review import from_folder as roof_panels
from plate_stock_review import from_folder as plate_stock
from exterior_field_stud_review import from_folder as exterior_field_studs
from wall_field_stud_review import from_folder as wall_field_studs
from header_cut_review import from_folder as header_cuts
from wall_panel_review import from_folder as wall_panels, import_wall_panels
from framing_stock_review import import_stock
from subfloor_panel_review import from_folder as subfloor_panels, joints_from_folder as subfloor_joints
from rafter_cut_review import from_folder as rafter_cuts
from framing_material_allowances import import_allowances
from company_scope_review import import_scope as import_company_scope
from wall_plate_reference import from_folder as wall_plate_reference,import_reference as import_wall_plate_reference
from owner_item_quantities import import_counts as import_owner_item_counts
from floor_finish_review import import_finish
from stair_quantity_review import import_stair
from count_reference_reviews import apply_count_reviews
from template_unit_reviews import reviewed_template
from measured_surface_costs import import_surfaces

def make_server(store,port=0):
    stair_path=store.folder/'stair_quantity_review.json'
    stair_bytes=stair_path.read_bytes() if stair_path.exists() else None
    stair_config=json.loads(stair_bytes) if stair_bytes is not None else None
    finish_path=store.folder/'floor_finish_review.json'
    finish_bytes=finish_path.read_bytes() if finish_path.exists() else None
    finish_config=json.loads(finish_bytes) if finish_bytes is not None else None
    rules_path=store.folder/'quantity_rules.json'
    rules_bytes=rules_path.read_bytes() if rules_path.exists() else None
    rules=json.loads(rules_bytes) if rules_bytes is not None else None
    reviews=ScopeReviews(store,rules) if rules is not None else None
    template_path=store.folder/'template_rows.json'
    template_bytes=template_path.read_bytes() if template_path.exists() else None
    template=json.loads(template_bytes) if template_bytes is not None else None
    unit_path=store.folder/'template_unit_reviews.json'
    unit_bytes=unit_path.read_bytes() if unit_path.exists() else None
    unit_config=json.loads(unit_bytes) if unit_bytes is not None else None
    applicability_path=store.folder/'scope_applicability.json'
    applicability_bytes=applicability_path.read_bytes() if applicability_path.exists() else None
    applicability=json.loads(applicability_bytes) if applicability_bytes is not None else None
    pricing_path=store.folder/'reviewed_prices.json'
    pricing_bytes=pricing_path.read_bytes() if pricing_path.exists() else None
    pricing=json.loads(pricing_bytes) if pricing_bytes is not None else None
    packages_path=store.folder/'reviewed_packages.json'
    packages_bytes=packages_path.read_bytes() if packages_path.exists() else None
    packages=json.loads(packages_bytes) if packages_bytes is not None else None
    snapshots_path=store.folder/'saved_trade_snapshots.json'
    snapshots_bytes=snapshots_path.read_bytes() if snapshots_path.exists() else None
    snapshots=json.loads(snapshots_bytes) if snapshots_bytes is not None else None
    links_path=store.folder/'linked_quantity_reviews.json'
    links_bytes=links_path.read_bytes() if links_path.exists() else None
    links=json.loads(links_bytes) if links_bytes is not None else None
    components_path=store.folder/'framing_component_review.json'
    components_bytes=components_path.read_bytes() if components_path.exists() else None
    components=json.loads(components_bytes) if components_bytes is not None else None
    wall_panels_path=store.folder/'wall_panel_review.json'
    wall_panels_bytes=wall_panels_path.read_bytes() if wall_panels_path.exists() else None
    wall_panels_config=json.loads(wall_panels_bytes) if wall_panels_bytes is not None else None
    stock_path=store.folder/'framing_stock_review.json'
    stock_bytes=stock_path.read_bytes() if stock_path.exists() else None
    stock_config=json.loads(stock_bytes) if stock_bytes is not None else None
    material_path=store.folder/'framing_material_allowances.json'
    material_bytes=material_path.read_bytes() if material_path.exists() else None
    material_config=json.loads(material_bytes) if material_bytes is not None else None
    company_scope_path=store.folder/'company_scope_review.json'
    company_scope_bytes=company_scope_path.read_bytes() if company_scope_path.exists() else None
    company_scope=json.loads(company_scope_bytes) if company_scope_bytes is not None else None
    plate_reference_path=store.folder/'wall_plate_reference.json'
    plate_reference_bytes=plate_reference_path.read_bytes() if plate_reference_path.exists() else None
    plate_reference_config=json.loads(plate_reference_bytes) if plate_reference_bytes is not None else None
    kits_path=store.folder/'kit_purchase_review.json'
    kits_bytes=kits_path.read_bytes() if kits_path.exists() else None
    kits=json.loads(kits_bytes) if kits_bytes is not None else None
    openings_path=store.folder/'opening_quantity_review.json'
    openings_bytes=openings_path.read_bytes() if openings_path.exists() else None
    openings_config=json.loads(openings_bytes) if openings_bytes is not None else None
    enclosures_path=store.folder/'enclosure_quantity_review.json'
    enclosures_bytes=enclosures_path.read_bytes() if enclosures_path.exists() else None
    enclosures_config=json.loads(enclosures_bytes) if enclosures_bytes is not None else None
    owner_counts_path=store.folder/'owner_item_quantities.json'
    owner_counts_bytes=owner_counts_path.read_bytes() if owner_counts_path.exists() else None
    owner_counts=json.loads(owner_counts_bytes) if owner_counts_bytes is not None else None
    count_reviews_path=store.folder/'count_reference_reviews.json'
    count_reviews_bytes=count_reviews_path.read_bytes() if count_reviews_path.exists() else None
    count_reviews=json.loads(count_reviews_bytes) if count_reviews_bytes is not None else None
    surfaces_path=store.folder/'measured_surface_costs.json'
    surfaces_bytes=surfaces_path.read_bytes() if surfaces_path.exists() else None
    surfaces_config=json.loads(surfaces_bytes) if surfaces_bytes is not None else None
    with fitz.open(store.plan) as doc:
        images={page:doc[page-1].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False).tobytes('png')
                for page in {m['page'] for m in store.config['measurements']}}
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def trusted(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def respond(self,status,value,content_type='application/json'):
            raw=value if isinstance(value,bytes) else encode(value).encode()
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.trusted():return self.respond(403,{'error':'Use the local review address'})
            try:
                store.check_source()
                if self.path=='/':return self.respond(200,Path(__file__).with_suffix('.html').read_bytes(),'text/html; charset=utf-8')
                if self.path=='/api/state':return self.respond(200,store.read())
                if self.path=='/api/window-cross-view':
                    from window_cross_view_review import from_folder as cross_view_windows
                    value=cross_view_windows(store.folder)
                    if value is None:return self.respond(404,{'error':'Reviewed floor and elevation pages required'})
                    return self.respond(200,value)
                if self.path=='/api/area-schedule-check':
                    from area_schedule_check import from_folder as area_schedule_check
                    value=area_schedule_check(store.folder,store.read())
                    if value is None:return self.respond(404,{'error':'No printed area inventory available'})
                    return self.respond(200,value)
                if self.path=='/api/paint-surfaces':
                    if not (store.folder/'paint_surface_review.json').exists():return self.respond(404,{'error':'No paint surface mapping configured'})
                    from paint_surface_review import from_folder as paint_surfaces
                    return self.respond(200,paint_surfaces(store.folder,store.read()))
                if self.path=='/api/roof-partition':
                    from roof_partition_state import from_folder as roof_partition
                    return self.respond(200,roof_partition(store.folder))
                if self.path=='/api/roof-bid-scope':
                    from roof_bid_scope import from_folder as roof_bid_scope
                    return self.respond(200,roof_bid_scope(store.folder))
                if self.path=='/api/roof-junctions':
                    roof=roof_panels(store.folder)
                    return self.respond(200,{**roof['junctions'],
                        **{k:roof[k] for k in ('plan_sha256','source_version','source_geometry_sha256','mapping_sha256','gradient_sha256')}})
                if self.path=='/api/roof-material-quantities':
                    from roof_material_quantities import from_folder as roof_material_quantities
                    return self.respond(200,roof_material_quantities(store.folder))
                if self.path=='/api/wall-runs':return self.respond(200,wall_runs(store.read(),wall_classification(store.folder)))
                if self.path=='/api/wall-plate-reference':
                    if plate_reference_config is None:return self.respond(404,{'error':'No wall plate reference configured'})
                    if plate_reference_path.read_bytes()!=plate_reference_bytes:raise EditConflict('Wall plate mapping changed; restart and review')
                    return self.respond(200,wall_plate_reference(store.folder,store.read(),plate_reference_config))
                if self.path=='/api/opening-schedule':return self.respond(200,opening_schedule(store.folder,store.read()))
                if self.path=='/api/opening-bid-scope':return self.respond(200,opening_bid_scope(store.folder,store.read()))
                if self.path=='/api/opening-framing-scope':
                    from opening_framing_scope import from_folder as opening_framing_scope
                    return self.respond(200,opening_framing_scope(store.folder,store.read()))
                if self.path=='/api/wall-enclosures':return self.respond(200,wall_enclosures(store.folder,store.read()))
                if self.path=='/api/floor-sundries':
                    if not (store.folder/'floor_sundries_review.json').exists():return self.respond(404,{'error':'No floor sundries review configured'})
                    from floor_sundries_review import from_folder as floor_sundries
                    return self.respond(200,floor_sundries(store.folder,store.read()))
                if self.path=='/api/room-regions':return self.respond(200,room_regions(store.folder,store.read()))
                if self.path=='/api/drywall-bid-scope':return self.respond(200,drywall_bid_scope(store.folder,store.read()))
                if self.path=='/api/wall-gap-labels':return self.respond(200,wall_gap_labels(store.plan,store.read(),wall_classification(store.folder),wall_alignment(store.folder)))
                if self.path=='/api/opening-headers':
                    if not (store.folder/'opening_header_review.json').exists():return self.respond(404,{'error':'No opening/header mapping configured'})
                    return self.respond(200,opening_headers(store.folder,store.read()))
                if self.path=='/api/roof-panels':
                    if not (store.folder/'roof_panel_review.json').exists():return self.respond(404,{'error':'No roof panel review configured'})
                    return self.respond(200,roof_panels(store.folder))
                if self.path=='/api/wall-panels':
                    if not (store.folder/'wall_panel_review.json').exists():return self.respond(404,{'error':'No wall panel review configured'})
                    return self.respond(200,wall_panels(store.folder))
                if self.path=='/api/subfloor-panels':
                    if not (store.folder/'subfloor_panel_review.json').exists():return self.respond(404,{'error':'No subfloor panel review configured'})
                    return self.respond(200,subfloor_panels(store.folder))
                if self.path=='/api/subfloor-joints':
                    if not (store.folder/'subfloor_panel_review.json').exists():return self.respond(404,{'error':'No subfloor panel review configured'})
                    return self.respond(200,subfloor_joints(store.folder))
                if self.path=='/api/plate-stock':
                    if not (store.folder/'plate_stock_review.json').exists():return self.respond(404,{'error':'No plate stock review configured'})
                    return self.respond(200,plate_stock(store.folder))
                if self.path=='/api/window-sill-stock':
                    if not (store.folder/'window_sill_stock_review.json').exists():return self.respond(404,{'error':'No window sill stock review configured'})
                    from window_sill_stock_review import from_folder as window_sills
                    return self.respond(200,window_sills(store.folder))
                if self.path=='/api/below-window-stock':
                    if not (store.folder/'below_window_stock_review.json').exists():return self.respond(404,{'error':'No below-window stock review configured'})
                    from below_window_stock_review import from_folder as below_windows
                    return self.respond(200,below_windows(store.folder))
                if self.path=='/api/window-header-clearance':
                    if not (store.folder/'window_header_clearance_review.json').exists():return self.respond(404,{'error':'No window header clearance review configured'})
                    from window_header_clearance_review import from_folder as window_clearance
                    return self.respond(200,window_clearance(store.folder))
                if self.path=='/api/frieze-routes':
                    if not (store.folder/'frieze_route_review.json').exists():return self.respond(404,{'error':'No frieze route mapping configured'})
                    from frieze_route_review import from_folder as frieze_routes
                    return self.respond(200,frieze_routes(store.folder))
                if self.path=='/api/header-cuts':
                    if not (store.folder/'header_cut_review.json').exists():return self.respond(404,{'error':'No header cutting review configured'})
                    return self.respond(200,header_cuts(store.folder))
                if self.path=='/api/rafter-cuts':
                    if not (store.folder/'rafter_cut_review.json').exists():return self.respond(404,{'error':'No rafter cutting review configured'})
                    return self.respond(200,rafter_cuts(store.folder))
                if self.path=='/api/exterior-field-studs':
                    if not (store.folder/'exterior_field_stud_review.json').exists():return self.respond(404,{'error':'No exterior field-stud review configured'})
                    return self.respond(200,exterior_field_studs(store.folder))
                if self.path=='/api/wall-stud-stock':
                    if not (store.folder/'stud_stock_review.json').exists():return self.respond(404,{'error':'No stud stock review configured'})
                    from stud_stock_review import from_folder as stud_stock
                    return self.respond(200,stud_stock(store.folder))
                if self.path=='/api/wall-field-studs':
                    if not (store.folder/'interior_field_stud_review.json').exists():return self.respond(404,{'error':'No combined wall field-stud review configured'})
                    return self.respond(200,wall_field_studs(store.folder))
                if self.path=='/api/scope-reviews':
                    if reviews is None:return self.respond(404,{'error':'No quantity mapping configured'})
                    if not rules_path.exists() or rules_path.read_bytes()!=rules_bytes:
                        raise EditConflict('Quantity rules changed; restart and verify the mapping')
                    return self.respond(200,{'rules_sha256':reviews.rules_sha256,'reviews':reviews.history()})
                if self.path in ('/api/quantities','/api/estimate-draft','/api/readiness','/api/export-snapshot','/api/estimate-summary','/api/company-scope-bids','/api/floor-finish'):
                    if rules is None:return self.respond(404,{'error':'No quantity mapping configured'})
                    if not rules_path.exists() or rules_path.read_bytes()!=rules_bytes:
                        raise EditConflict('Quantity rules changed; restart and verify the mapping')
                    if self.path in ('/api/estimate-draft','/api/readiness','/api/export-snapshot','/api/estimate-summary','/api/company-scope-bids','/api/floor-finish'):
                        if template is None:return self.respond(404,{'error':'No template rows configured'})
                        if not template_path.exists() or template_path.read_bytes()!=template_bytes:
                            raise EditConflict('Template rows changed; restart and verify the template')
                        state=store.read()
                        effective_template=template
                        if unit_config is not None:
                            if not unit_path.exists() or unit_path.read_bytes()!=unit_bytes:
                                raise EditConflict('Template unit review changed; restart and verify')
                            effective_template=reviewed_template(template,unit_config,store.folder,state['plan_sha256'])
                        value=template_draft(state,reviews.effective_rules(),effective_template)
                        if self.path=='/api/floor-finish':
                            if finish_config is None:return self.respond(404,{'error':'No room finish mapping configured'})
                            if not finish_path.exists() or finish_path.read_bytes()!=finish_bytes:
                                raise EditConflict('Room finish mapping changed; restart and verify')
                            floor=import_finish(value,state,finish_config,store.folder)['floor_finish_review']
                            return self.respond(200,{'floor_finish_review':floor,'estimate_released':False,
                                'whole_house_total':None,'basis':'Floor area references only; whole-estimate reviews and prices are separate.'})
                        if plate_reference_config is not None:
                            if plate_reference_path.read_bytes()!=plate_reference_bytes:raise EditConflict('Wall plate mapping changed; restart and review')
                            value=import_wall_plate_reference(value,wall_plate_reference(store.folder,state,plate_reference_config))
                        if company_scope is not None:
                            if not company_scope_path.exists() or company_scope_path.read_bytes()!=company_scope_bytes:
                                raise EditConflict('Company scope mapping changed; restart and verify')
                            value=import_company_scope(value,store.folder,company_scope,state)
                        if links is not None:
                            if not links_path.exists() or links_path.read_bytes()!=links_bytes:
                                raise EditConflict('Linked review mapping changed; restart and verify')
                            value=import_linked_quantities(value,links,store.folder,source_state=state)
                        if surfaces_config is not None:
                            if not surfaces_path.exists() or surfaces_path.read_bytes()!=surfaces_bytes:
                                raise EditConflict('Supplemental surface mapping changed; restart and verify')
                            value=import_surfaces(value,surfaces_config,store.folder)
                        if snapshots is not None:
                            if not snapshots_path.exists() or snapshots_path.read_bytes()!=snapshots_bytes:
                                raise EditConflict('Saved trade configuration changed; restart and verify')
                            value=import_saved_trades(value,state,snapshots,store.folder)
                        if components is not None:
                            if not components_path.exists() or components_path.read_bytes()!=components_bytes:
                                raise EditConflict('Framing component mapping changed; restart and verify')
                            value=import_components(value,state,components,store.folder)
                        if wall_panels_config is not None and 'template_row' in wall_panels_config:
                            if not wall_panels_path.exists() or wall_panels_path.read_bytes()!=wall_panels_bytes:
                                raise EditConflict('Wall panel mapping changed; restart and verify')
                            value=import_wall_panels(value,store.folder,wall_panels_config['template_row'],
                                hashlib.sha256(wall_panels_bytes).hexdigest())
                        if stock_config is not None:
                            if not stock_path.exists() or stock_path.read_bytes()!=stock_bytes:
                                raise EditConflict('Framing stock mapping changed; restart and verify')
                            value=import_stock(value,store.folder,stock_config)
                        if (store.folder/'paint_surface_review.json').exists():
                            from paint_surface_review import import_references as import_paint_references
                            value=import_paint_references(value,store.folder,state)
                        value['template_sha256']=hashlib.sha256(template_bytes).hexdigest()
                        value['rules_sha256']=hashlib.sha256(rules_bytes).hexdigest()
                        if applicability is not None:
                            if not applicability_path.exists() or applicability_path.read_bytes()!=applicability_bytes:
                                raise EditConflict('Scope applicability changed; restart and verify the decisions')
                            value=apply_applicability(value,applicability,store.folder/'scope_evidence')
                        if openings_config is not None:
                            if not openings_path.exists() or openings_path.read_bytes()!=openings_bytes:
                                raise EditConflict('Opening quantity mapping changed; restart and verify')
                            value=import_opening_quantities(value,state,openings_config,store.folder)
                        if kits is not None:
                            if not kits_path.exists() or kits_path.read_bytes()!=kits_bytes:
                                raise EditConflict('Kit purchase mapping changed; restart and verify')
                            value=import_kit_purchases(value,kits,store.folder)
                        if enclosures_config is not None:
                            if not enclosures_path.exists() or enclosures_path.read_bytes()!=enclosures_bytes:
                                raise EditConflict('Floor scope mapping changed; restart and verify')
                            value=import_enclosure_quantities(value,state,enclosures_config,store.folder)
                        if owner_counts is not None:
                            if not owner_counts_path.exists() or owner_counts_path.read_bytes()!=owner_counts_bytes:
                                raise EditConflict('Owner item mapping changed; restart and verify')
                            value=import_owner_item_counts(value,owner_counts,store.folder)
                        if finish_config is not None:
                            if not finish_path.exists() or finish_path.read_bytes()!=finish_bytes:
                                raise EditConflict('Room finish mapping changed; restart and verify')
                            value=import_finish(value,state,finish_config,store.folder)
                        if stair_config is not None:
                            if not stair_path.exists() or stair_path.read_bytes()!=stair_bytes:
                                raise EditConflict('Stair mapping changed; restart and review')
                            value=import_stair(value,stair_config,store.folder)
                        from tile_purchase import apply_purchase as apply_tile_purchase
                        value=apply_tile_purchase(value,store.folder)
                        if packages is not None:
                            if not packages_path.exists() or packages_path.read_bytes()!=packages_bytes:
                                raise EditConflict('Package mapping changed; restart and verify the quotes')
                            value=price_packages(value,packages,date.today().isoformat(),store.folder/'price_evidence',withhold_stale=True)
                        if pricing is not None:
                            if not pricing_path.exists() or pricing_path.read_bytes()!=pricing_bytes:
                                raise EditConflict('Price mapping changed; restart and verify the prices')
                            value=price_draft(value,pricing,date.today().isoformat(),store.folder/'price_evidence')
                        if material_config is not None:
                            if not material_path.exists() or material_path.read_bytes()!=material_bytes:
                                raise EditConflict('Framing material mapping changed; restart and verify')
                            value=import_allowances(value,store.folder,material_config,date.today().isoformat())
                        if count_reviews is not None:
                            if not count_reviews_path.exists() or count_reviews_path.read_bytes()!=count_reviews_bytes:
                                raise EditConflict('Count verification mapping changed; restart and verify')
                            value=apply_count_reviews(value,count_reviews,store.folder)
                        from customer_price_review import apply_customer_prices
                        value=apply_customer_prices(value,store.folder)
                        if self.path=='/api/readiness':value=readiness(value,effective_template)
                        elif self.path=='/api/estimate-summary':value=review_summary(value,template)
                        elif self.path=='/api/export-snapshot':value=export_snapshot(value,effective_template)
                        elif self.path=='/api/company-scope-bids':
                            from company_scope_bids import build_scopes
                            value=build_scopes(value)
                    else:value=rollup(store.read(),reviews.effective_rules())
                    value['rules_sha256']=hashlib.sha256(rules_bytes).hexdigest()
                    return self.respond(200,value)
                if self.path.startswith('/sheet/') and self.path.endswith('.png'):
                    page=int(self.path[len('/sheet/'):-4])
                    if page in images:return self.respond(200,images[page],'image/png')
                return self.respond(404,{'error':'Not found'})
            except EditConflict as exc:self.respond(409,{'error':str(exc)})
            except (ValueError,KeyError,TypeError,OSError) as exc:self.respond(400,{'error':str(exc)})
        def do_POST(self):
            origins={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if not self.trusted() or self.headers.get('Origin') not in origins or self.headers.get('Content-Type')!='application/json':
                return self.respond(403,{'error':'Save from this local review window'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=128000:raise ValueError('Invalid request size')
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError('Expected a measurement edit')
                if self.path=='/api/scope-review':
                    if reviews is None:return self.respond(404,{'error':'No quantity mapping configured'})
                    if not rules_path.exists() or rules_path.read_bytes()!=rules_bytes:
                        raise EditConflict('Quantity rules changed; restart and verify the mapping')
                    if set(payload)!={'rule_id','measurement_id','decision','scope','reviewer','base_version','plan_sha256','rules_sha256'}:
                        raise ValueError('Review requires rule, measurement, decision, scope, reviewer and source versions')
                    return self.respond(200,reviews.save(**payload))
                if self.path=='/api/save':
                    if set(payload)!={'measurement_id','points','base_version','plan_sha256','note'}:
                        raise ValueError('Save requires measurement, points, version, drawing identity and note')
                    return self.respond(200,store.save(**payload))
                if self.path=='/api/preview':
                    if set(payload)!={'measurement_id','points'}:raise ValueError('Invalid preview')
                    state=store.read();measurement=state['measurements'][payload['measurement_id']]
                    return self.respond(200,calculate({**measurement,'points':payload['points']}))
                return self.respond(404,{'error':'Not found'})
            except EditConflict as exc:self.respond(409,{'error':str(exc)})
            except (ValueError,KeyError,TypeError) as exc:self.respond(400,{'error':str(exc)})
    return http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',required=True)
    parser.add_argument('--port',type=int,default=5814);args=parser.parse_args()
    server=make_server(MeasurementStore(args.job),args.port)
    print(f'Framing draft editor: http://127.0.0.1:{server.server_port}/',flush=True)
    server.serve_forever()
