"""Fresh CN+S/Horizons checks; does not modify the application on another computer."""
import csv,json,math
from datetime import datetime,timedelta,timezone
import numpy as np
import spiceypy as spice
from lunar_geometry import ROOT,Engine,FRAME,SPICE_LOCK,enu_basis,separation_deg,horizons_reference
from catalog import SITES

OUT=ROOT/'results'/'cns_decision_review'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    engine=Engine()
    sites={s.id:s for s in SITES}
    heights={sid:json.loads((ROOT/'results'/f'{sid}.json').read_text(encoding='utf-8'))['surface_elevation_m']
             for sid in ['apollo11','scr-study','im2']}
    start=datetime(2026,11,14,12,tzinfo=timezone.utc)
    stamp=lambda d:d.isoformat(timespec='microseconds').replace('+00:00','Z')
    def elev(sid,d,body):
        return engine.bodies(sites[sid],stamp(d),heights[sid])[body]['apparent']['elevation_deg']
    def crossing(sid,body):
        left=start;fl=elev(sid,left,body)
        for k in range(1,121):
            right=start+timedelta(hours=6*k);fr=elev(sid,right,body)
            if fl*fr<0:
                while (right-left).total_seconds()>0.02:
                    mid=left+(right-left)/2;fm=elev(sid,mid,body)
                    if fl*fm<=0:right=mid
                    else:left=mid;fl=fm
                # One minute after mathematical centre crossing; not a terrain event.
                return right+timedelta(seconds=60)
            left=right;fl=fr
        raise ValueError('No ideal centre crossing in scan')
    cases=[('apollo11',start,'baseline'),('scr-study',start,'baseline'),('im2',start,'earth near ideal horizon'),
           ('apollo11',crossing('apollo11','sun'),'sun near ideal horizon'),
           ('scr-study',crossing('scr-study','earth'),'earth near ideal horizon')]
    rows=[];full=[]
    for sid,date,note in cases:
        site=sites[sid];utc=stamp(date);out=engine.bodies(site,utc,heights[sid])
        ref=horizons_reference(site,utc,heights[sid],cache_dir=OUT/'horizons')
        basis=enu_basis(site.latitude_deg,site.longitude_deg)
        with SPICE_LOCK:et=spice.str2et(date.strftime('%Y-%m-%d %H:%M:%S.%f')+' UTC')
        for name in ['sun','earth']:
            actual=out[name]['apparent'];reference=ref[name]
            with SPICE_LOCK:
                lt,_=spice.spkcpo(name.upper(),et,FRAME,'OBSERVER','LT+S',np.array(out['observer_xyz_m'])/1000,'MOON',FRAME)
            ltlocal=basis@np.array(lt[:3])
            error=separation_deg(actual['direction_enu'],reference['direction_enu'])
            row={'site':sid,'case':note,'utc':utc,'latitude_deg':site.latitude_deg,'longitude_east_deg':site.longitude_deg,
                 'surface_height_m':heights[sid],'observer_radial_height_m':2.,'frame':FRAME,'body':name,
                 'correction':'CN+S','local_az_deg':actual['azimuth_deg'],'local_el_deg':actual['elevation_deg'],
                 'horizons_az_deg':reference['azimuth_deg'],'horizons_el_deg':reference['elevation_deg'],
                 'separation_deg':error,'LTplusS_vs_CNplusS_deg':separation_deg(ltlocal,actual['direction_enu']),
                 'T01_proposed_deg':0.001,'pass_T01':error<=0.001,'diagnostic_above_1e5_deg':error>0.00001,
                 'reference_file':reference['reference_file']}
            rows.append(row)
            print(sid,utc,name,'CN/Horizons',error,'LT/CN',row['LTplusS_vs_CNplusS_deg'],flush=True)
        full.append({'case':note,'calculation':out,'horizons':ref})
    for filename,data in [('comparisons.json',rows),('full_results.json',full)]:
        (OUT/filename).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    with (OUT/'comparisons.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'checks':len(rows),'all_pass':all(r['pass_T01'] for r in rows),
             'max_separation_deg':max(r['separation_deg'] for r in rows),
             'max_LT_CN_separation_deg':max(r['LTplusS_vs_CNplusS_deg'] for r in rows),
             'checked_at':datetime.now(timezone.utc).isoformat(),
             'scope':'local prototype only; other-computer application not inspected; conditional on adopted coordinates/frame'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
