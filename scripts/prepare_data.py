"""Prepare small, reproducible chart datasets; never overwrite source downloads."""
from pathlib import Path
import csv, hashlib, io, json, math
import numpy as np
import pandas as pd
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data'
OUT = SRC / 'prepared'
OUT.mkdir(exist_ok=True)
START, END = '2024-01-01', '2026-01-01'
report = {'analysis_start': START, 'analysis_end_inclusive': '2025-12-31', 'checks': {}, 'outputs': {}}

def save(df, name):
    assert not df.columns.duplicated().any()
    df.to_csv(OUT / name, index=False, float_format='%.4f', na_rep='')
    report['outputs'][name] = {'rows': len(df), 'columns': list(df.columns), 'bytes': (OUT/name).stat().st_size}

def blocks(name):
    return [pd.read_csv(io.StringIO(b)) for b in (SRC/name).read_text(encoding='utf-8-sig').strip().split('\n\n')]

def distance(lat1, lon1, lat2, lon2):
    a,b,c,d = map(math.radians, [lat1,lon1,lat2,lon2])
    return 6371 * 2 * math.asin(min(1, math.sqrt(math.sin((c-a)/2)**2 + math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2)))

aqmeta, current, aq = blocks('Malaysia Air Quality.csv')
wm, wh, wd = blocks('Malaysia Weather.csv')
# Labels inferred from coordinates; source exports do not retain requested place names.
labels = ['Kuala Lumpur area','George Town area','Ipoh area','Johor Bahru area','Kuantan area',
          'Unconfirmed location (4.4N, 101.1E)','Kuching area','Miri area','Kota Kinabalu area']
locations = aqmeta.rename(columns={'location_id':'air_source_id','latitude':'air_latitude','longitude':'air_longitude'})
locations['location_key'] = ['L%02d' % i for i in locations.air_source_id]
locations['location_label'] = labels
locations['label_status'] = ['inferred_from_coordinates' if i != 5 else 'unconfirmed' for i in locations.air_source_id]
locations['include_in_city_comparisons'] = locations.air_source_id != 5
mapping = {}
for _, w in wm.iterrows():
    distances = locations.apply(lambda a: distance(w.latitude,w.longitude,a.air_latitude,a.air_longitude), axis=1)
    idx = distances.idxmin()
    assert distances[idx] < 15, 'Unmatched weather location'
    assert idx not in mapping.values(), 'Ambiguous weather matching'
    mapping[int(w.location_id)] = idx
    for col,val in [('weather_source_id',int(w.location_id)),('weather_latitude',w.latitude),('weather_longitude',w.longitude),('grid_separation_km',distances[idx])]:
        locations.loc[idx,col] = val
locations['weather_source_id'] = locations.weather_source_id.astype('Int64')
save(locations[['location_key','location_label','label_status','include_in_city_comparisons','air_source_id','air_latitude','air_longitude','weather_source_id','weather_latitude','weather_longitude','grid_separation_km']], 'locations.csv')
airkeys = dict(zip(locations.air_source_id, locations.location_key))
weatherkeys = {k: locations.loc[v,'location_key'] for k,v in mapping.items()}
aq = aq.rename(columns={'pm2_5 (μg/m³)':'pm25_ugm3','pm10 (μg/m³)':'pm10_ugm3'})
aq['location_key'] = aq.location_id.map(airkeys)
aq['time'] = pd.to_datetime(aq.time)
aq = aq[(aq.time >= START) & (aq.time < END)].copy()
assert not aq.duplicated(['location_key','time']).any()
assert aq[['pm25_ugm3','pm10_ugm3']].notna().all().all()
assert (aq[['pm25_ugm3','pm10_ugm3']] >= 0).all().all()
assert len(aq) == 9 * 731 * 24
aq['date'] = aq.time.dt.strftime('%Y-%m-%d')
daily = aq.groupby(['location_key','date']).agg(pm25_mean_ugm3=('pm25_ugm3','mean'),pm25_max_hourly_ugm3=('pm25_ugm3','max'),pm10_mean_ugm3=('pm10_ugm3','mean'),valid_hours=('pm25_ugm3','count')).reset_index()
assert daily.valid_hours.eq(24).all()
wh = wh.rename(columns={'temperature_2m (°C)':'temperature_c','wind_speed_100m (km/h)':'wind100_kmh','wind_speed_10m (km/h)':'wind10_kmh','precipitation (mm)':'precipitation_mm','rain (mm)':'rain_mm','wind_direction_100m (°)':'wind_direction100_deg'})
wh['location_key'] = wh.location_id.map(weatherkeys)
wh['time'] = pd.to_datetime(wh.time)
wh = wh[(wh.time >= START) & (wh.time < END)].copy()
assert len(wh) == 7 * 731 * 24
assert not wh.duplicated(['location_key','time']).any()
assert wh.notna().all().all()
wh['date'] = wh.time.dt.strftime('%Y-%m-%d')
wday = wh.groupby(['location_key','date']).agg(temperature_mean_c=('temperature_c','mean'),temperature_min_c=('temperature_c','min'),temperature_max_c=('temperature_c','max'),precipitation_mm=('precipitation_mm','sum'),wind10_mean_kmh=('wind10_kmh','mean'),wind100_mean_kmh=('wind100_kmh','mean'),weather_hours=('time','count')).reset_index()
# Independent daily export check for precipitation totals.
wd['location_key'] = wd.location_id.map(weatherkeys)
wd = wd[(wd.time >= START) & (wd.time < END)]
check = wday.merge(wd[['location_key','time','precipitation_sum (mm)']],left_on=['location_key','date'],right_on=['location_key','time'],validate='one_to_one')
rain_difference = float((check.precipitation_mm - check['precipitation_sum (mm)']).abs().max())
report['checks']['max_hourly_vs_exported_daily_precipitation_difference_mm'] = rain_difference
assert rain_difference <= 0.11
daily = daily.merge(wday,on=['location_key','date'],how='left',validate='one_to_one')
daily['has_weather'] = daily.weather_hours.notna()
save(daily,'location_daily.csv')
daily['month'] = daily.date.str[:7] + '-01'
monthly = daily.groupby(['location_key','month']).agg(pm25_mean_ugm3=('pm25_mean_ugm3','mean'),pm25_min_daily_ugm3=('pm25_mean_ugm3','min'),pm25_max_daily_ugm3=('pm25_mean_ugm3','max'),pm10_mean_ugm3=('pm10_mean_ugm3','mean'),days=('date','size'),temperature_mean_c=('temperature_mean_c','mean'),wind10_mean_kmh=('wind10_mean_kmh','mean'),weather_days=('weather_hours','count')).reset_index()
rain = daily.groupby(['location_key','month']).precipitation_mm.sum(min_count=1).reset_index()
monthly = monthly.merge(rain,on=['location_key','month'],validate='one_to_one')
save(monthly,'location_monthly.csv')
daily['year'] = daily.date.str[:4].astype(int)
annual = daily.groupby(['location_key','year']).agg(pm25_mean_ugm3=('pm25_mean_ugm3','mean'),pm10_mean_ugm3=('pm10_mean_ugm3','mean'),pm25_p95_daily_ugm3=('pm25_mean_ugm3',lambda s:s.quantile(.95)),days=('date','size')).reset_index()
annual = annual.merge(locations[['location_key','location_label','air_latitude','air_longitude','include_in_city_comparisons']],on='location_key',validate='many_to_one')
save(annual,'location_annual.csv')
# Box plots and histograms should use the daily file, not averages of monthly means.
joined = wh.merge(aq[['location_key','time','pm25_ugm3']],on=['location_key','time'],validate='one_to_one')
joined['direction_index'] = np.floor(((joined.wind_direction100_deg % 360)+11.25)/22.5).astype(int)%16
joined['speed_band'] = pd.cut(joined.wind100_kmh,[0,1,5,10,20,float('inf')],right=False,labels=['0-<1','1-<5','5-<10','10-<20','20+'])
rose = joined.groupby(['location_key','direction_index','speed_band'],observed=True).agg(hours=('time','size'),pm25_mean_ugm3=('pm25_ugm3','mean')).reset_index()
rose['direction'] = rose.direction_index.map(dict(enumerate(['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'])))
rose['direction_degrees'] = rose.direction_index*22.5
rose['percent_hours'] = rose.hours/rose.groupby('location_key').hours.transform('sum')*100
assert np.allclose(rose.groupby('location_key').percent_hours.sum(),100)
save(rose,'wind_rose.csv')

# National monitoring context, keeping missing values and pollutant units explicit.
nat = pd.read_csv(SRC/'air_pollution_co.csv')
nat['pollutant'] = nat.pollutant.replace({'PM 2.5':'PM2.5','PM 10':'PM10'})
nat['unit'] = np.where(nat.pollutant.isin(['PM2.5','PM10']),'ug/m3','ppm')
nat['is_missing'] = nat.concentration.isna()
save(nat,'national_pollution_monthly.csv')
w = openpyxl.load_workbook(SRC/'data.xlsx',read_only=True,data_only=True)
s = w.active; s.reset_dimensions(); r = list(s.iter_rows(values_only=True)); who = pd.DataFrame(r[3:],columns=r[2])
who = who[['Location','Period','Dim1','FactValueNumeric','FactValueNumericLow','FactValueNumericHigh','DateModified']].rename(columns={'Location':'country','Period':'year','Dim1':'residence_type','FactValueNumeric':'pm25_ugm3','FactValueNumericLow':'lower_bound','FactValueNumericHigh':'upper_bound','DateModified':'source_modified'})
save(who.sort_values(['year','residence_type']),'who_residence_annual.csv')
w.close()

# Preserve source geometry, simplifying only property names and serialization.
geo = json.loads((SRC/'malaysia_states.geojson.geojson').read_text())
def ring_area_km2(ring):
    # Spherical surface integral, radius 6371.0088 km; suitable for regional display.
    total=0
    for i in range(len(ring)):
        x1,y1=ring[i-1][:2];x2,y2=ring[i][:2]
        total += math.radians(x2-x1)*(math.sin(math.radians(y1))+math.sin(math.radians(y2)))
    return abs(total)*6371.0088**2/2
state_areas={}
for f in geo['features']:
    p = f['properties'];f['properties']={'state_code':p['shapeISO'],'state_name':p['shapeName']}
    geom=f['geometry'];parts=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
    state_areas[p['shapeISO']]=sum(ring_area_km2(part[0])-sum(ring_area_km2(h) for h in part[1:]) for part in parts)
    assert state_areas[p['shapeISO']]>0
(OUT/'malaysia_states.geojson').write_text(json.dumps(geo,separators=(',',':')),encoding='utf-8')

# Ray casting with holes; bounding boxes avoid scanning unrelated state vertices.
def in_ring(x,y,ring):
    inside=False
    for i in range(len(ring)):
        x1,y1=ring[i-1][:2];x2,y2=ring[i][:2]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
            inside=not inside
    return inside

polygons=[]
for f in geo['features']:
    geom=f['geometry'];parts=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
    for part in parts:
        xs,ys=zip(*[(v[0],v[1]) for v in part[0]])
        polygons.append((min(xs),min(ys),max(xs),max(ys),part,f['properties']['state_code']))
def state_of(x,y):
    for a,b,c,d,part,code in polygons:
        if a<=x<=c and b<=y<=d and in_ring(x,y,part[0]) and not any(in_ring(x,y,h) for h in part[1:]):return code
    return 'UNASSIGNED'

fire = pd.read_csv(SRC/'fire_archive_SV-C2_819336.csv',dtype={'acq_time':str})
fire['time_utc'] = pd.to_datetime(fire.acq_date+' '+fire.acq_time.str.zfill(4),format='%Y-%m-%d %H%M')
fire['time_local'] = fire.time_utc + pd.Timedelta(hours=8)
fire = fire[(fire.time_local>=START)&(fire.time_local<END)].copy()
report['checks']['fire_input_rows_in_local_period'] = len(fire)
report['checks']['fire_type_counts_before_filter'] = {str(k):int(v) for k,v in fire.type.value_counts().items()}
fire = fire[(fire.type==0)&fire.confidence.isin(['n','h'])].copy()
assert not fire.duplicated().any()
fire['date'] = fire.time_local.dt.strftime('%Y-%m-%d')
fire['year'] = fire.time_local.dt.year
fire['month'] = fire.time_local.dt.strftime('%Y-%m-01')
fire['state_code'] = [state_of(x,y) for x,y in zip(fire.longitude,fire.latitude)]
fire['frp_mw'] = fire.frp
save(fire[['date','latitude','longitude','state_code','confidence','frp_mw','daynight']],'fire_points.csv')
report['checks']['fire_retained_rows'] = len(fire)
report['checks']['fire_unassigned_points'] = int(fire.state_code.eq('UNASSIGNED').sum())
fday = fire.groupby('date').agg(detections=('date','size'),mean_frp_mw=('frp_mw','mean')).reindex(pd.date_range(START,'2025-12-31').strftime('%Y-%m-%d')).rename_axis('date').reset_index()
fday['detections'] = fday.detections.fillna(0).astype(int)
save(fday,'fire_daily.csv')
state_names = {f['properties']['state_code']:f['properties']['state_name'] for f in geo['features']}
state_names['UNASSIGNED']='Outside or unmatched to simplified boundaries'
fstate = fire.groupby(['state_code','year']).agg(detections=('date','size'),high_confidence_detections=('confidence',lambda s:int((s=='h').sum())),mean_frp_mw=('frp_mw','mean'))
fstate = fstate.reindex(pd.MultiIndex.from_product([state_names,[2024,2025]],names=['state_code','year'])).reset_index()
for c in ['detections','high_confidence_detections']:fstate[c]=fstate[c].fillna(0).astype(int)
fstate['high_confidence_percent'] = fstate.high_confidence_detections/fstate.detections.replace(0,np.nan)*100
fstate['state_name'] = fstate.state_code.map(state_names)
fstate['boundary_area_km2'] = fstate.state_code.map(state_areas)
fstate['detections_per_1000_km2'] = fstate.detections/fstate.boundary_area_km2*1000
save(fstate,'fire_state_annual.csv')
assert fstate.detections.sum()==len(fire)==fday.detections.sum()
# Equal angular rectangular cells, explicitly counts rather than physical-area density.
fire['lon_bin'] = np.floor(fire.longitude*4).astype(int)
fire['lat_bin'] = np.floor(fire.latitude*4).astype(int)
bins = fire.groupby(['year','lon_bin','lat_bin']).agg(detections=('date','size'),mean_frp_mw=('frp_mw','mean')).reset_index()
bins['west']=bins.lon_bin/4;bins['south']=bins.lat_bin/4;bins['east']=bins.west+.25;bins['north']=bins.south+.25
bins['longitude']=bins.west+.125;bins['latitude']=bins.south+.125
save(bins.drop(columns=['lon_bin','lat_bin']),'fire_spatial_bins.csv')
assert bins.detections.sum()==len(fire)
features=[]
for r in bins.to_dict('records'):
    a,b,c,d=r['west'],r['south'],r['east'],r['north']
    features.append({'type':'Feature','properties':{'year':r['year'],'detections':r['detections'],'mean_frp_mw':round(r['mean_frp_mw'],4)},'geometry':{'type':'Polygon','coordinates':[[[a,b],[c,b],[c,d],[a,d],[a,b]]]}})
(OUT/'fire_spatial_bins.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')),encoding='utf-8')

report['checks'].update({'air_hourly_rows':len(aq),'weather_hourly_rows':len(wh),'daily_rows':len(daily),'daily_weather_matched_rows':int(daily.has_weather.sum()),'air_missing_values_in_period':int(aq[['pm25_ugm3','pm10_ugm3']].isna().sum().sum()),'unique_air_locations':9,'unique_weather_locations':7,'source_files_unchanged':True})
report['sources'] = {p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in SRC.iterdir() if p.is_file()}
report['prepared_data_bytes'] = sum(p.stat().st_size for p in OUT.iterdir() if p.suffix in ['.csv','.geojson'])
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'checks':report['checks'],'prepared_data_bytes':report['prepared_data_bytes'],'outputs':{k:v['rows'] for k,v in report['outputs'].items()}},indent=2))
