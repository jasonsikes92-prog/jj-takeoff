import sys, math, collections, statistics; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
exec(open('scale_lock.py').read().split('def clean_spans')[0].split('PPF=')[0].replace("PPF={}",""))

def raw_spans(page):
    H,V=hv(page); res=[]
    for ft,s,r in labels(page):
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        for y,runs in H.items():
            if abs(y-cy)>20: continue
            L=[x for x in runs if x[1]<r.x0+2 and x[1]>r.x0-30]
            R=[x for x in runs if x[0]>r.x1-2 and x[0]<r.x1+30]
            if len(L)!=1 or len(R)!=1: continue
            res.append((ft, R[0][1]-L[0][0], s,'H'))
        for x,runs in V.items():
            if abs(x-cx)>20: continue
            U=[t for t in runs if t[1]<r.y0+2 and t[1]>r.y0-30]
            D=[t for t in runs if t[0]>r.y1-2 and t[0]<r.y1+30]
            if len(U)!=1 or len(D)!=1: continue
            res.append((ft, D[0][1]-U[0][0], s,'V'))
    return res

def regress(page,label,nominal):
    pts=[(f,s) for f,s,_,_ in raw_spans(page) if 3<s/f<40]
    if len(pts)<3: print(f'{label}: too few ({len(pts)})'); return None
    # trim outliers vs nominal+offset model
    for _ in range(3):
        n=len(pts); mx=statistics.mean(p[0] for p in pts); my=statistics.mean(p[1] for p in pts)
        sxx=sum((p[0]-mx)**2 for p in pts); sxy=sum((p[0]-mx)*(p[1]-my) for p in pts)
        m=sxy/sxx; b=my-m*mx
        resid=[abs(p[1]-(m*p[0]+b)) for p in pts]
        sd=statistics.pstdev(resid) or 1
        pts=[p for p,r in zip(pts,resid) if r<=3*sd+1.0]
        if len(pts)==n: break
    r2num=sum(( (m*p[0]+b) - statistics.mean(q[1] for q in pts))**2 for p in pts)
    r2den=sum(( p[1]-statistics.mean(q[1] for q in pts))**2 for p in pts)
    print(f'{label:<18} n={len(pts):<3} ppf={m:7.4f}  end-tick short={-b:6.2f} pts  R2={r2num/r2den:.6f}   nominal {nominal}  err {100*(m-nominal)/nominal:+.2f}%')
    return m

d=fitz.open(PDF)
regress(d[2],'p3 FDN PLUMB',18.0)
regress(d[3],'p4 SLAB',9.0)
regress(d[4],'p5 MAIN FLOOR',18.0)
regress(d[5],'p6 ROOF',18.0)
