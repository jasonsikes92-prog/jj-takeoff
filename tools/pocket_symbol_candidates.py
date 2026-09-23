"""Find a partially retracted rectangular leaf inside a drawn wall pocket."""
import math


def pocket_matches(gap,nominal_width,scale,lines):
    """Use inch coordinates along/across the gap; do not infer from a bare tag."""
    length=math.dist(*gap);u=[(gap[1][i]-gap[0][i])/length for i in range(2)]
    def project(p):
        d=[p[i]-gap[0][i] for i in range(2)]
        return [(d[0]*u[0]+d[1]*u[1])*12/scale,(-d[0]*u[1]+d[1]*u[0])*12/scale]
    width=length*12/scale;parallel=[];cross=[]
    for line in lines:
        a,b=map(project,line['points'])
        if max(abs(a[1]),abs(b[1]))>4:continue
        if min(a[0],b[0]) < -nominal_width-4 or max(a[0],b[0])>width+nominal_width+4:continue
        if abs(a[1]-b[1])<=.05 and abs(abs(a[0]-b[0])-nominal_width)<=1:
            parallel.append({'start':min(a[0],b[0]),'end':max(a[0],b[0]),'v':(a[1]+b[1])/2,'line':line})
        elif abs(a[0]-b[0])<=.05:
            cross.append({'u':(a[0]+b[0])/2,'lo':min(a[1],b[1]),'hi':max(a[1],b[1]),'line':line})
    def closure(at,lo,hi):
        return next((c['line'] for c in cross if abs(c['u']-at)<=.15 and abs(c['lo']-lo)<=.15 and abs(c['hi']-hi)<=.15),None)
    pairs=[]
    for i,a in enumerate(parallel):
        for b in parallel[i+1:]:
            lo,hi=sorted((a['v'],b['v']))
            if not .75<=hi-lo<=4 or abs(a['start']-b['start'])>.15 or abs(a['end']-b['end'])>.15:continue
            start,end=(a['start']+b['start'])/2,(a['end']+b['end'])/2
            pairs.append({'start':start,'end':end,'lo':lo,'hi':hi,'rails':[a['line'],b['line']],
                'start_cap':closure(start,lo,hi),'end_cap':closure(end,lo,hi)})
    matches=[]
    for cavity in pairs:
        if not 1.5<=cavity['hi']-cavity['lo']<=4 or abs(cavity['hi']+cavity['lo'])/2>.75:continue
        side=(0 if abs(cavity['end'])<=3 and cavity['start']<=-nominal_width*.8 and cavity['start_cap'] else
              1 if abs(cavity['start']-width)<=3 and cavity['end']>=width+nominal_width*.8 and cavity['end_cap'] else None)
        if side is None:continue
        mouth=cavity['end'] if side==0 else cavity['start']
        for leaf in pairs:
            if not leaf['start_cap'] or not leaf['end_cap'] or not .75<=leaf['hi']-leaf['lo']<=2:continue
            if not cavity['lo']+.1<=leaf['lo']<leaf['hi']<=cavity['hi']-.1:continue
            if abs((leaf['lo']+leaf['hi']-cavity['lo']-cavity['hi'])/2)>.25:continue
            if not leaf['start']+nominal_width*.2<=mouth<=leaf['end']-nominal_width*.2:continue
            if side==0 and (leaf['start']<cavity['start']-.15 or leaf['end']>width+.15):continue
            if side==1 and (leaf['end']>cavity['end']+.15 or leaf['start']<-.15):continue
            key=[side,cavity['start'],cavity['end'],cavity['lo'],cavity['hi'],leaf['start'],leaf['end'],leaf['lo'],leaf['hi']]
            if any(max(abs(a-b) for a,b in zip(key,m['geometry_key_inches']))<.02 for m in matches):continue
            matches.append({'configuration':'pocket','method':'native_retracted_leaf_inside_wall_pocket',
                'pocket_gap_endpoint':side,'geometry_key_inches':key,'cavity':cavity,'leaf':leaf})
    return matches
