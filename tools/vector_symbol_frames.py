"""Find explicit closed rectangular vector frames as corroborating symbol evidence."""
import numpy as np


def rectangle_frames(page,ink,tolerance=.15):
    vertical=[];horizontal=[]
    for path in page.get_drawings():
        color=path.get('color')
        if color is None:continue
        if ink=='red':selected=color[0]>color[1]+35/255 and color[0]>color[2]+35/255
        elif ink=='dark':selected=max(color)<200/255
        else:raise ValueError('Choose explicit red or dark symbol ink')
        if not selected:continue
        lines=[]
        for item in path['items']:
            if item[0]=='l':lines.append((item[1],item[2]))
            elif item[0]=='re':
                r=item[1];lines.extend([(r.tl,r.tr),(r.tr,r.br),(r.br,r.bl),(r.bl,r.tl)])
        for a,b in lines:
            if abs(a.x-b.x)<=tolerance and abs(a.y-b.y)>=3:
                vertical.append(((a.x+b.x)/2,min(a.y,b.y),max(a.y,b.y),path['seqno']))
            elif abs(a.y-b.y)<=tolerance and abs(a.x-b.x)>=3:
                horizontal.append(((a.y+b.y)/2,min(a.x,b.x),max(a.x,b.x),path['seqno']))
    if not vertical or not horizontal:return []
    v=np.array(vertical);h=np.array(horizontal);found={}
    for left in v:
        peers=v[(v[:,0]>left[0]+3)&(abs(v[:,1]-left[1])<=tolerance)&(abs(v[:,2]-left[2])<=tolerance)]
        for right in peers:
            ends=h[(abs(h[:,1]-left[0])<=tolerance)&(abs(h[:,2]-right[0])<=tolerance)]
            top=ends[abs(ends[:,0]-left[1])<=tolerance];bottom=ends[abs(ends[:,0]-left[2])<=tolerance]
            if not len(top) or not len(bottom):continue
            bounds=[float(left[0]),float(left[1]),float(right[0]),float(left[2])]
            key=tuple(round(n,2) for n in bounds)
            found[key]={'bbox_pt':bounds,'path_sequence_numbers':sorted({int(n) for n in [left[3],right[3],top[0,3],bottom[0,3]]})}
    return sorted(found.values(),key=lambda f:f['bbox_pt'])


def corroborate_frames(candidates,frames,reference):
    enclosed=[f for f in frames if all((f['bbox_pt'][i]>=reference[i] if i<2 else f['bbox_pt'][i]<=reference[i]) for i in range(4))]
    if not enclosed:raise ValueError('No closed vector rectangle inside this legend reference')
    frame=max(enclosed,key=lambda f:(f['bbox_pt'][2]-f['bbox_pt'][0])*(f['bbox_pt'][3]-f['bbox_pt'][1]))
    a,b,c,d=frame['bbox_pt'];ref_ratio=(c-a)/(d-b);kept=[];rejected=[]
    for candidate in candidates:
        x0,y0,x1,y1=candidate['bbox_pt'];rotation=candidate['rotation_degrees']
        ratio=1/ref_ratio if rotation in (90,270) else ref_ratio
        possible=[]
        for f in frames:
            a,b,c,d=f['bbox_pt']
            if not (x0<=a<c<=x1 and y0<=b<d<=y1):continue
            if abs((c-a)/(d-b)/ratio-1)>.08:continue
            if abs((a+c)/2-candidate['point_pt'][0])>2 or abs((b+d)/2-candidate['point_pt'][1])>2:continue
            possible.append(f)
        if len(possible)==1:kept.append({**candidate,'vector_frame':possible[0]})
        else:rejected.append({**candidate,'frame_rejection':'No unique matching closed rectangle'})
    return kept,rejected,frame
