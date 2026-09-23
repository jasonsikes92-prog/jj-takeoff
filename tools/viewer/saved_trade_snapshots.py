"""Import saved trade quantities only while their reviewed geometry is unchanged."""
import hashlib
from measurement_store import encode
from slab_snapshot_bridge import import_slab_snapshot
from foundation_snapshot_bridge import import_foundation_snapshot
from window_snapshot_bridge import import_window_snapshot
from framing_snapshot_bridge import import_framing_snapshot
from bearing_slab_quantities import import_bearing_slab


def import_saved_trades(draft, state, config, folder):
    if config['plan_sha256'] != draft['plan_sha256']:
        raise ValueError('Saved trades belong to another drawing')
    digest = hashlib.sha256(encode(state['measurements']).encode()).hexdigest()
    if digest != config['measurements_sha256']:
        return {**draft, 'withheld_supplemental_cost_ids':[identity for item in config['snapshots']
                    for identity in item.get('supplemental_mappings',{})], 'saved_trade_review_required':
                'Measurements changed; saved trade quantities withheld pending recalculation'}
    result = draft
    importers = {'slab': import_slab_snapshot, 'foundation': import_foundation_snapshot,
                 'windows': import_window_snapshot, 'framing': import_framing_snapshot}
    for item in config['snapshots']:
        if 'window_geometry_mapping_sha256' in item:
            if item['trade']!='windows':raise ValueError('Window geometry mapping requires the window trade')
            from window_sill_stock_review import from_folder as window_geometry
            checked=window_geometry(folder)
            if (checked['mapping_sha256']!=item['window_geometry_mapping_sha256']
                    or checked['plan_sha256']!=draft['plan_sha256']
                    or checked['measurement_version']!=state['version']):
                raise ValueError('Window snapshot geometry mapping or revision changed')
            if checked['changed_measurements']:
                result={**result,'saved_trade_review_required':
                    'Window dimensions changed; window quantities, accessories and prices need review',
                    'withheld_supplemental_cost_ids':result.get('withheld_supplemental_cost_ids',[])+list(item.get('supplemental_mappings',{}))}
                continue
        dependency=item.get('linked_review_geometry')
        if dependency:
            job=str((folder/dependency['job']).resolve())
            linked=next((r for r in draft.get('linked_quantity_reviews',[]) if r['job']==job),{})
            if linked.get('geometry_sha256')!=dependency['sha256']:
                result={**result,'saved_trade_review_required':
                    'Linked geometry changed; affected saved trade quantities withheld pending recalculation',
                    'withheld_supplemental_cost_ids':result.get('withheld_supplemental_cost_ids',[])+list(item.get('supplemental_mappings',{}))}
                continue
        source = (folder / item['file']).resolve()
        if not source.is_relative_to(folder.resolve()):
            raise ValueError('Saved trade source must be inside the job')
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Saved trade source changed')
        options={'supplemental_mappings':item['supplemental_mappings']} if item['trade'] in ('slab','foundation') and 'supplemental_mappings' in item else {}
        result = importers[item['trade']](result, source, item['mappings'],**options)
    if config.get('bearing_slab'):
        result = import_bearing_slab(result, config['bearing_slab'], folder)
    return result
