"""LunarHorizon: explicit lunar frames, SPICE geometry, DEM terrain and Horizons checks.

All Cartesian positions in this module are metres except values passed to SPICE
or Horizons, whose units are kilometres. Angles exposed by the API are degrees.
This is a reproducible scientific prototype, not a flight-qualified product.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
import spiceypy as spice

RADIUS_M = 1737400.0
FRAME = 'MOON_ME_DE440_ME421'
ROOT = Path(__file__).resolve().parent
SPICE_LOCK = threading.RLock()

def unit(v):
    v = np.asarray(v, dtype=float)
    length = np.linalg.norm(v, axis=-1, keepdims=True)
    if np.any(length == 0):
        raise ValueError('Zero direction vector')
    return v / length

def enu_basis(latitude_deg, longitude_deg):
    phi, lam = np.deg2rad([latitude_deg, longitude_deg])
    east = np.array([-np.sin(lam), np.cos(lam), 0.0])
    north = np.array([-np.sin(phi)*np.cos(lam), -np.sin(phi)*np.sin(lam), np.cos(phi)])
    up = np.array([np.cos(phi)*np.cos(lam), np.cos(phi)*np.sin(lam), np.sin(phi)])
    return np.array([east, north, up])

def xyz(latitude_deg, longitude_deg, elevation_m=0):
    lat, lon = np.deg2rad(latitude_deg), np.deg2rad(longitude_deg)
    r = RADIUS_M + np.asarray(elevation_m)
    return np.stack([r*np.cos(lat)*np.cos(lon),r*np.cos(lat)*np.sin(lon),r*np.sin(lat)],axis=-1)

def latlon(position):
    v = np.asarray(position)
    return np.rad2deg(np.arctan2(v[...,2], np.hypot(v[...,0],v[...,1]))), np.rad2deg(np.arctan2(v[...,1],v[...,0]))

def azel(direction_enu):
    e,n,u = np.asarray(direction_enu)
    horizontal = math.hypot(e,n)
    az = math.degrees(math.atan2(e,n)) % 360 if horizontal > 1e-12*np.linalg.norm(direction_enu) else None
    return az, math.degrees(math.atan2(u,horizontal))

def direction_enu(azimuth_deg, elevation_deg):
    a,e = np.deg2rad([azimuth_deg,elevation_deg])
    return np.array([np.cos(e)*np.sin(a), np.cos(e)*np.cos(a), np.sin(e)])

def incidence_deg(normal_enu, sun_enu):
    return float(np.rad2deg(np.arccos(np.clip(np.dot(unit(normal_enu),unit(sun_enu)),-1,1))))

def separation_deg(a,b):
    a,b=unit(a),unit(b)
    return float(np.rad2deg(np.arctan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b))))

@dataclass(frozen=True)
class Site:
    id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    catalog_elevation_m: float | None
    status: str
    source_url: str
    def __post_init__(self):
        if not math.isfinite(self.latitude_deg) or not -90 <= self.latitude_deg <= 90:
            raise ValueError('Latitude outside [-90,90]')
        if not math.isfinite(self.longitude_deg) or not -180 <= self.longitude_deg <= 180:
            raise ValueError('Longitude must be east-positive in [-180,180]')

def parse_utc(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp requires Z or explicit offset')
    dt=dt.astimezone(timezone.utc)
    if not 1962 <= dt.year < 2150:
        raise ValueError('Prototype UTC coverage is restricted to 1962 <= year < 2150; kernels are also checked at runtime')
    return dt

class Engine:
    def __init__(self, kernel_dir=None):
        self.kernel_dir=Path(kernel_dir or ROOT/'data'/'kernels')
        names=['naif0012.tls','de440s.bsp','pck00011.tpc','moon_pa_de440_200625.bpc','moon_de440_250416.tf']
        with SPICE_LOCK:
            for name in names:
                p=self.kernel_dir/name
                if not p.is_file(): raise FileNotFoundError(f'{p}; run download_kernels.py')
                spice.furnsh(str(p))

    def bodies(self,site,utc,elevation_m,observer_height_m=2.0):
        dt=parse_utc(utc)
        if not math.isfinite(elevation_m) or not math.isfinite(observer_height_m) or observer_height_m<0:
            raise ValueError('Finite surface height and nonnegative observer height required')
        p=xyz(site.latitude_deg,site.longitude_deg,elevation_m+observer_height_m)
        basis=enu_basis(site.latitude_deg,site.longitude_deg)
        result={}
        with SPICE_LOCK:
            et=spice.str2et(dt.strftime('%Y-%m-%d %H:%M:%S.%f')+' UTC')
            for name in ('SUN','EARTH'):
                modes={}
                for label, correction in [('geometric','NONE'),('apparent','CN+S')]:
                    state,light_time=spice.spkcpo(name,et,FRAME,'OBSERVER',correction,p/1000,'MOON',FRAME)
                    v=np.array(state[:3])*1000
                    local=basis@unit(v)
                    a,e=azel(local)
                    modes[label]={'azimuth_deg':a,'elevation_deg':e,'direction_enu':local.tolist(),
                                  'range_km':float(np.linalg.norm(v)/1000),'light_time_s':float(light_time),
                                  'correction':correction}
                result[name.lower()]=modes
        return {'utc':dt.isoformat().replace('+00:00','Z'),'frame':FRAME,'observer_xyz_m':p.tolist(),
                'surface_elevation_m':elevation_m,'observer_height_m':observer_height_m,
                'ephemeris':'DE440s','apparent_limit':'CN+S: converged light-time and stellar aberration; no gravitational light deflection',
                'pole_convention':'North/east at exact pole are defined by supplied longitude',**result}

class Terrain:
    """Read a local GeoTIFF crop, honoring its mask, scale and pixel-centre convention."""
    def __init__(self,path):
        import rasterio
        from pyproj import Transformer
        self.path=Path(path)
        self.manifest=json.loads(self.path.with_suffix('.json').read_text(encoding='utf-8'))
        with rasterio.open(path) as src:
            arr=src.read(1,masked=True).astype(float)
            self.values=arr.filled(np.nan)*src.scales[0]+src.offsets[0]
            self.transform=src.transform
            self.to_xy=Transformer.from_crs(src.crs.geodetic_crs if hasattr(src.crs,'geodetic_crs') else
                __import__('pyproj').CRS.from_user_input(src.crs).geodetic_crs,src.crs,always_xy=True)

    def sample(self,lat,lon):
        lat,lon=np.broadcast_arrays(np.asarray(lat,dtype=float),np.asarray(lon,dtype=float))
        x,y=self.to_xy.transform(lon,lat)
        col,row=(~self.transform)*(x,y)
        col=np.asarray(col)-0.5;row=np.asarray(row)-0.5
        c0=np.floor(col).astype(int);r0=np.floor(row).astype(int)
        good=(r0>=0)&(c0>=0)&(r0+1<self.values.shape[0])&(c0+1<self.values.shape[1])
        rr=np.clip(r0,0,self.values.shape[0]-2);cc=np.clip(c0,0,self.values.shape[1]-2)
        fc=col-c0;fr=row-r0
        a,b,c,d=self.values[rr,cc],self.values[rr,cc+1],self.values[rr+1,cc],self.values[rr+1,cc+1]
        out=(1-fr)*((1-fc)*a+fc*b)+fr*((1-fc)*c+fc*d)
        return np.where(good,out,np.nan)

    def normal(self,site,baseline_m=None):
        # Fit an ENU plane to a 3x3 stencil on the sphere; axes are true ENU,
        # not the DEM's projected grid north. This avoids polar convergence errors.
        baseline=float(baseline_m or self.manifest['normal_baseline_m'])
        basis=enu_basis(site.latitude_deg,site.longitude_deg)
        center_height=float(self.sample(site.latitude_deg,site.longitude_deg))
        if not math.isfinite(center_height): raise ValueError('Missing DEM at site')
        p=xyz(site.latitude_deg,site.longitude_deg,center_height)
        offsets=np.array([(x,y) for x in (-baseline,0,baseline) for y in (-baseline,0,baseline)])
        radii=np.linalg.norm(offsets,axis=1)
        tangent=offsets[:,0,None]*basis[0]+offsets[:,1,None]*basis[1]
        tangent/=np.maximum(radii[:,None],1)
        u=basis[2]*np.cos(radii[:,None]/RADIUS_M)+tangent*np.sin(radii[:,None]/RADIUS_M)
        lat,lon=latlon(u)
        h=self.sample(lat,lon)
        if not np.all(np.isfinite(h)): raise ValueError('Incomplete stencil: cannot determine terrain normal')
        points=(xyz(lat,lon,h)-p)@basis.T
        design=np.column_stack([points[:,:2],np.ones(len(points))])
        east_slope,north_slope,offset=np.linalg.lstsq(design,points[:,2],rcond=None)[0]
        normal=unit([-east_slope,-north_slope,1.0])
        slope=math.degrees(math.atan(math.hypot(east_slope,north_slope)))
        aspect=math.degrees(math.atan2(-east_slope,-north_slope))%360 if slope>1e-10 else None
        return {'normal_enu':normal.tolist(),'slope_deg':slope,'downslope_azimuth_deg':aspect,
                'surface_elevation_m':center_height,'baseline_m':baseline,
                'plane_residual_rms_m':float(np.sqrt(np.mean((design@np.array([east_slope,north_slope,offset])-points[:,2])**2)))}

    def horizon(self,site,azimuths_deg,observer_height_m=2.0,max_distance_m=40000,step_m=100):
        if max_distance_m<=0 or step_m<=0 or step_m>max_distance_m:
            raise ValueError('Invalid horizon sampling')
        az=np.atleast_1d(np.asarray(azimuths_deg,dtype=float))
        distances=np.arange(step_m,max_distance_m+step_m/2,step_m)
        basis=enu_basis(site.latitude_deg,site.longitude_deg)
        h0=float(self.sample(site.latitude_deg,site.longitude_deg))
        if not math.isfinite(h0): raise ValueError('Missing DEM at observer')
        a=np.deg2rad(az)[:,None,None]
        t=np.sin(a)*basis[0]+np.cos(a)*basis[1]
        theta=distances[None,:,None]/RADIUS_M
        u=np.cos(theta)*basis[2]+np.sin(theta)*t
        lat,lon=latlon(u)
        h=self.sample(lat,lon)
        observer=xyz(site.latitude_deg,site.longitude_deg,h0+observer_height_m)
        local=(xyz(lat,lon,h)-observer)@basis.T
        elevation=np.rad2deg(np.arctan2(local[...,2],np.hypot(local[...,0],local[...,1])))
        rows=[]
        for i, angle in enumerate(az):
            valid=np.isfinite(elevation[i])
            if not np.any(valid):
                rows.append({'azimuth_deg':float(angle%360),'elevation_deg':None,'complete_within_sampled_domain':False})
                continue
            k=int(np.nanargmax(elevation[i]))
            rows.append({'azimuth_deg':float(angle%360),'elevation_deg':float(elevation[i,k]),
                         'obstacle_distance_m':float(distances[k]),'valid_fraction':float(np.mean(valid)),
                         'complete_within_sampled_domain':bool(np.all(valid))})
        return {'rays':rows,'max_distance_m':max_distance_m,'radial_step_m':step_m,
                'quality':'finite-radius sampled DEM horizon, not a certified physical horizon; obstacles between samples or beyond radius are not excluded',
                'source':self.manifest['source_url']}

def calculate(site,utc,engine,terrain=None,observer_height_m=2.0,max_distance_m=40000,step_m=100):
    normal=terrain.normal(site) if terrain else None
    elevation=normal['surface_elevation_m'] if normal else site.catalog_elevation_m
    if elevation is None: raise ValueError('Surface elevation required; not silently replaced by zero')
    result=engine.bodies(site,utc,elevation,observer_height_m)
    sun=result['sun']['apparent'];earth=result['earth']['apparent']
    result['site']={**site.__dict__,'coordinate_frame':'ME, closely aligned to DE421','height_source':'DEM' if terrain else 'catalog'}
    result['earth_ideal_horizon']={'elevation_deg':earth['elevation_deg'],'azimuth_deg':earth['azimuth_deg'],
                                   'center_above_ideal_plane':earth['elevation_deg']>0}
    result['sun']['incidence_ideal_plane_deg']=90-sun['elevation_deg']
    result['terrain']=normal
    result['sun']['incidence_terrain_deg']=incidence_deg(normal['normal_enu'],sun['direction_enu']) if normal else None
    if terrain:
        directions=[sun['azimuth_deg'],earth['azimuth_deg']]
        if any(a is None for a in directions): raise ValueError('Zenith/nadir azimuth undefined for ray calculation')
        horizon=terrain.horizon(site,directions,observer_height_m,max_distance_m,step_m)
        result['terrain_horizon']=horizon
        for body,ray in zip(('sun','earth'),horizon['rays']):
            elev=result[body]['apparent']['elevation_deg']
            clearance=elev-ray['elevation_deg'] if ray['elevation_deg'] is not None else None
            result[body]['terrain_clearance_deg']=clearance
            result[body]['center_above_sampled_horizon']=(clearance>0) if clearance is not None and ray['complete_within_sampled_domain'] else None
        result['sun']['local_surface_faces_sun']=result['sun']['incidence_terrain_deg']<90
    else:
        result['terrain_horizon']=None
    return result

def horizons_reference(site,utc,elevation_m,observer_height_m=2.0,cache_dir=None):
    """Fetch Horizons airless apparent AZ/EL; common JPL models, not independent observations."""
    dt=parse_utc(utc)
    cache=Path(cache_dir or ROOT/'results'/'horizons');cache.mkdir(parents=True,exist_ok=True)
    output={}
    for body,number in [('sun','10'),('earth','399')]:
        params={'format':'json','COMMAND':number,'EPHEM_TYPE':'OBSERVER','CENTER':'coord@301',
                'COORD_TYPE':'GEODETIC','SITE_COORD':f'{site.longitude_deg:.10f},{site.latitude_deg:.10f},{(elevation_m+observer_height_m)/1000:.12f}',
                'TLIST':dt.strftime('%Y-%m-%d %H:%M:%S.%f'),'TLIST_TYPE':'CAL',
                'QUANTITIES':'4,20','CSV_FORMAT':'YES','APPARENT':'AIRLESS','EXTRA_PREC':'YES',
                'TIME_TYPE':'UT','TIME_DIGITS':'FRACSEC','CAL_TYPE':'GREGORIAN'}
        query={k:v if k=='format' else "'"+v+"'" for k,v in params.items()}
        url='https://ssd.jpl.nasa.gov/api/horizons.api?'+urlencode(query)
        key=hashlib.sha256(url.encode()).hexdigest()[:20]
        path=cache/f'{site.id}_{body}_{key}.json'
        if path.exists(): saved=json.loads(path.read_text(encoding='utf-8'))
        else:
            payload=json.loads(urlopen(url,timeout=60).read())
            if 'error' in payload: raise RuntimeError(payload['error'])
            saved={'url':url,'params':params,'retrieved_at':datetime.now(timezone.utc).isoformat(),'response':payload}
            path.write_text(json.dumps(saved,indent=2),encoding='utf-8')
        text=saved['response'].get('result','')
        if '$$SOE' not in text: raise RuntimeError('Horizons did not return an ephemeris')
        line=text.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()[0]
        row=next(csv.reader(io.StringIO(line)))
        a,e=float(row[3]),float(row[4])
        center_frame=re.search(r'Center pole/equ\s*:\s*(.*)',text)
        if not center_frame or not any(f in center_frame.group(1) for f in ('MEAN_ME','MOON_ME')):
            raise ValueError('Unexpected Horizons lunar frame; comparison refused')
        output[body]={'azimuth_deg':a,'elevation_deg':e,'direction_enu':direction_enu(a,e).tolist(),
                      'range_km':float(row[5])*149597870.7,'reference_file':str(path.relative_to(ROOT)),
                      'center_frame_header':center_frame.group(1).strip()}
    return output
