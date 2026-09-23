"""Source-linked slope pairs; roof role and orthographic projection need review."""
import itertools
import math


def candidates(page,view_bounds_pt):
    if (not isinstance(view_bounds_pt,(list,tuple)) or len(view_bounds_pt)!=4
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in view_bounds_pt)):
        raise ValueError('Elevation view requires finite rectangle coordinates')
    a,b,c,d=view_bounds_pt
    if not 0<=a<c<=page.rect.width or not 0<=b<d<=page.rect.height:
        raise ValueError('Elevation view is outside the drawing')
    inside=lambda p:a<=p[0]<=c and b<=p[1]<=d
    apexes={}
    for ref,drawing in enumerate(page.get_drawings()):
        if (drawing.get('type')!='s' or drawing.get('color') is None
                or drawing.get('stroke_opacity',1)<=0 or drawing.get('dashes') not in ('[] 0',None)):continue
        style=(drawing['color'],round(drawing.get('width',0),5))
        for item in drawing['items']:
            if item[0]!='l':continue
            first,last=map(tuple,item[1:])
            if not inside(first) or not inside(last) or math.dist(first,last)<24:continue
            apex,tail=sorted((first,last),key=lambda point:point[1])
            dx=tail[0]-apex[0];dy=tail[1]-apex[1]
            if abs(dx)<1 or dy<1:continue
            rise=12*dy/abs(dx)
            if not 1<=rise<=24:continue
            key=(tuple(round(v,3) for v in apex),style)
            apexes.setdefault(key,[]).append({'apex':list(apex),'tail':list(tail),
                'rise_per_12':rise,'side':'left' if dx<0 else 'right','path':ref})
    found=[];seen=set()
    for edges in apexes.values():
        for left,right in itertools.product([e for e in edges if e['side']=='left'],[e for e in edges if e['side']=='right']):
            if abs(left['rise_per_12']/right['rise_per_12']-1)>.005:continue
            key=(tuple(left['apex']),tuple(left['tail']),tuple(right['tail']))
            if key in seen:continue
            seen.add(key)
            found.append({'page':page.number+1,'source_view_bounds_pt':list(view_bounds_pt),
                'apex_pt':left['apex'],'left_eave_pt':left['tail'],'right_eave_pt':right['tail'],
                'rise_per_12':(left['rise_per_12']+right['rise_per_12'])/2,
                'side_rises_per_12':[left['rise_per_12'],right['rise_per_12']],
                'source_cad_paths':[left['path'],right['path']],
                'source_method':'paired diagonal CAD edges in an elevation view',
                'interpretation':'Unclassified gable-shaped edges; verify roof identity, face-on view and equal axis scaling',
                'pitch_is_inferred':True,'pitch_certified':False})
    return {'candidates':found,'pitch_certified':False}
