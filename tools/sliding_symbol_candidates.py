"""Recognize two offset rectangular panels and the surrounding opening jambs."""
import math


def sliding_matches(gap,nominal_width,scale,lines):
    length=math.dist(*gap);u=[(gap[1][i]-gap[0][i])/length for i in range(2)]
    def project(p):
        d=[p[i]-gap[0][i] for i in range(2)]
        return [(d[0]*u[0]+d[1]*u[1])*12/scale,(-d[0]*u[1]+d[1]*u[0])*12/scale]
    width=length*12/scale;rails=[];cross=[]
    for line in lines:
        a,b=map(project,line['points'])
        if any(not -3<=p[0]<=width+3 or abs(p[1])>4 for p in (a,b)):continue
        if abs(a[1]-b[1])<.05 and abs(abs(a[0]-b[0])-nominal_width/2)<=2:
            rails.append((min(a[0],b[0]),max(a[0],b[0]),(a[1]+b[1])/2,line))
        elif abs(a[0]-b[0])<.05:
            cross.append(((a[0]+b[0])/2,min(a[1],b[1]),max(a[1],b[1]),line))
    panels=[]
    for i,a in enumerate(rails):
        for b in rails[i+1:]:
            lo,hi=sorted((a[2],b[2]))
            if abs(a[0]-b[0])>.15 or abs(a[1]-b[1])>.15 or not .75<=hi-lo<=2.25:continue
            caps=[next((c for c in cross if abs(c[0]-x)<.15 and abs(c[1]-lo)<.15 and abs(c[2]-hi)<.15),None)
                for x in (a[0],a[1])]
            if not all(caps):continue
            geometry=[a[0],a[1],lo,hi]
            if any(max(abs(x-y) for x,y in zip(geometry,p['geometry_inches']))<.02 for p in panels):continue
            panels.append({'geometry_inches':geometry,'rails':[a[3],b[3]],'caps':[c[3] for c in caps]})
    matches=[]
    for i,a in enumerate(panels):
        for b in panels[i+1:]:
            x,y=a['geometry_inches'],b['geometry_inches']
            # Separate adjacent tracks, partial overlap, and one panel at an outer jamb.
            separation=max(x[2],y[2])-min(x[3],y[3])
            overlap=min(x[1],y[1])-max(x[0],y[0])
            if not 0<=separation<=1 or not .2*nominal_width/2<=overlap<=.8*nominal_width/2:continue
            if not (min(abs(x[0]),abs(y[0]))<=2 or min(abs(width-x[1]),abs(width-y[1]))<=2):continue
            lo=min(x[2],y[2]);hi=max(x[3],y[3])
            jambs=[next((c for c in cross if abs(c[0]-at)<=.15 and c[1]<=lo+.15 and c[2]>=hi-.15),None)
                for at in (0,width)]
            if not all(jambs):continue
            matches.append({'configuration':'sliding_pair','method':'native_offset_closed_panels_between_jambs',
                'panels':[a,b],'jambs':[c[3] for c in jambs],'drawn_panel_count':2})
    return matches
