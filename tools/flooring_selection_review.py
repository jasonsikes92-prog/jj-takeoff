"""Resolve explicit room-to-Buildern selection links without importing old costs."""
import hashlib
import json
from pathlib import Path
from room_use_review import binding


def read_selections(folder,rooms):
    root=Path(folder).resolve();path=root/'flooring_selection_review.json'
    if not path.exists():return {'selections':{},'unresolved':[]}
    raw=path.read_bytes();config=json.loads(raw)
    if config['plan_sha256']!=rooms['plan_sha256']:raise ValueError('Floor selections belong to another plan')
    regions={r['id']:r for r in rooms['regions']};seen=set();resolved={};unresolved=[]
    for decision in config['decisions']:
        identity=decision['region_id']
        if not identity or identity in seen:raise ValueError('Floor selection room links must be unique')
        seen.add(identity);region=regions.get(identity)
        if region is None or decision['region_sha256']!=binding(rooms['plan_sha256'],region):
            unresolved.append({'region_id':identity,'reason':'Room boundary or labels changed; review selection coverage'})
            continue
        source=(root/decision['source_file']).resolve()
        if (not source.is_relative_to(root) or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest()!=decision['source_sha256']):
            raise ValueError('Saved floor selection evidence changed or is outside this job')
        document=json.loads(source.read_bytes())
        if document.get('projectId')!=config['project_id'] or not document.get('capturedAt'):
            raise ValueError('Floor selection evidence needs its project and capture date')
        records=document['response']['data']['selections']['data']
        matches=[r for r in records if r['id']==decision['selection_id']]
        if len(matches)!=1 or matches[0]['projectId']!=config['project_id']:
            raise ValueError('Floor selection identity or project is ambiguous')
        record=matches[0];selected=[i for i in record['items'] if i['status']=='SELECTED']
        matches=[i for i in selected if i['id']==decision['item_id']]
        if len(matches)!=1 or (record.get('optionSetting')=='SINGLE' and len(selected)!=1):
            unresolved.append({'region_id':identity,'reason':'Linked product is not uniquely selected in saved evidence'})
            continue
        item=matches[0]
        if not item.get('name'):raise ValueError('Selected flooring product needs a name')
        resolved[identity]={'product':item['name'],'brand':item.get('brand') or None,
            'sku':item.get('sku') or None,'url':item.get('url') or None,
            'selection_id':record['id'],'item_id':item['id'],'project_id':config['project_id'],
            'selection_name':record['name'],'source_file':decision['source_file'],
            'source_sha256':decision['source_sha256'],'captured_at':document['capturedAt'],
            'record_updated_at':record.get('updatedAt'),'status':'selected_in_saved_source',
            'region_sha256':decision['region_sha256'],'live_selection_verified':False,
            'historical_quantity_and_price_imported':False}
    return {'selections':resolved,'unresolved':unresolved,'mapping_sha256':hashlib.sha256(raw).hexdigest()}
