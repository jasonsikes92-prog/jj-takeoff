import sys, json, math; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J
K=1/math.cos(math.radians(45))          # 1.41421 foreshorten correction, rotated wing
walls=json.load(open('envelope_walls.json'))
rot=sum(w['len'] for w in walls if w['ang'] in (45,135,136))
ortho=sum(w['len'] for w in walls if w['ang'] not in (45,135,136))
band=json.load(open('wallband.json')); gab=json.load(open('gables.json'))
AREAS={'heated':3245.7,'garage':1038.5,'rear_porch':1168.8,'front_porch':76.8}
under=sum(AREAS.values())
H_GAR=10.375+0.6; H_MAIN=10.6+0.6
wall_band=rot*H_GAR + ortho*H_MAIN
gp={'E1_FRONT':456.4,'E3_REAR':317.3,'E2_LEFT':193.3,'E4_RIGHT':233.3}
gu={'E1_FRONT':188.0,'E3_REAR':31.4,'E2_LEFT':24.3,'E4_RIGHT':45.4}
gab_paired=sum(gp.values()); gab_unp=sum(gu.values())
gab_corr=gp['E4_RIGHT']*K + gp['E1_FRONT']*1.20 + gp['E3_REAR'] + gp['E2_LEFT']
tl=sum(band[k]['LAP'] for k in band); tb=sum(band[k]['B&B'] for k in band); ts=sum(band[k]['STONE'] for k in band)
tot=tl+tb+ts
stone_up=sum(gab[k]['STONE'] for k in gab)
stone_tot=(ts/tot)*wall_band + stone_up
gross_lo=wall_band+gab_paired; gross_hi=wall_band+gab_corr+gab_unp
gross=wall_band+gab_corr
rest=gross-stone_tot
lap=rest*tl/(tl+tb); bnb=rest*tb/(tl+tb)
out={
 'areas_certified':AREAS,'under_roof_sf':round(under,1),'heated_sf':AREAS['heated'],
 'exterior_wall_lf':{'total':round(rot+ortho,2),'rotated45_garage_wing':round(rot,2),'orthogonal':round(ortho,2)},
 'wall_heights_ft':{'garage_wing':H_GAR,'main_house':H_MAIN},
 'cladding_sf':{'wall_band':round(wall_band,0),'gables_paired_asdrawn':round(gab_paired,0),
   'gables_foreshorten_corrected':round(gab_corr,0),'gables_unpaired_extra':round(gab_unp,0),
   'GROSS_total':round(gross,0),'range_lo':round(gross_lo,0),'range_hi':round(gross_hi,0)},
 'material_split_pct_from_wall_band':{'LAP':round(100*tl/tot,1),'B&B':round(100*tb/tot,1),'STONE':round(100*ts/tot,1)},
 'cladding_by_material_sf':{'STONE_mason_scope':round(stone_tot,0),'LAP_hardie':round(lap,0),'BNB_hardie':round(bnb,0)},
 'roof':{'footprint_sf':6159.0,'overhang_ft':1.5,'perimeter_lf':402.0,
   'shingle_surface_sf':4859.7,'metal_surface_sf':1822.5,'total_surface_sf':6682.2},
}
zones=[{'footprint_sf':4346.8,'pitch':6}]
out['roof']['shingle_turnkey']=J.roofing_turnkey(zones)
out['roof']['shingle_decoded_xcheck']=J.roofing_estimate(zones, hip_ridge_lf=0, drip_edge_lf=402.0, n_pipe_boots=1)
print(json.dumps(out,indent=1,default=str)[:3200])
json.dump(out,open('takeoff.json','w'),indent=1,default=str)
