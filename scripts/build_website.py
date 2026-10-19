"""Build browser data and readable Vega-Lite specifications from prepared inputs."""
from pathlib import Path
import pandas as pd
import numpy as np
import json, math, copy

ROOT=Path(__file__).resolve().parents[1];P=ROOT/'data/prepared';D=ROOT/'data/site';S=ROOT/'specs'
D.mkdir(exist_ok=True);S.mkdir(exist_ok=True)
formats={}
def output(df,name):
    if name in ['daily','fire-points']:
        df=df.copy();parse={}
        for col in df:
            if pd.api.types.is_bool_dtype(df[col]):
                parse[col]='boolean';df[col]=df[col].map({True:'true',False:'false'})
            elif pd.api.types.is_numeric_dtype(df[col]):parse[col]='number'
        df.to_csv(D/(name+'.csv'),index=False,float_format='%.3f',na_rep='')
        formats[name]={'type':'csv','parse':parse}
        old=D/(name+'.json')
        if old.exists():old.unlink()
    else:
        (D/(name+'.json')).write_text(df.to_json(orient='records',double_precision=3),encoding='utf-8')
loc=pd.read_csv(P/'locations.csv');loc=loc[loc.include_in_city_comparisons].copy();loc['city']=loc.location_label.str.replace(' area','',regex=False)
names=dict(zip(loc.location_key,loc.city));cities=list(names.values());keys=list(names)
day=pd.read_csv(P/'location_daily.csv');day=day[day.location_key.isin(keys)].copy();day['city']=day.location_key.map(names);day['year']=day.date.str[:4].astype(int)
day['jitter']=[((i*7919)%997)/997-.5 for i in range(len(day))]
day=day.rename(columns={'pm25_mean_ugm3':'pm25','precipitation_mm':'rain','temperature_mean_c':'temperature','wind10_mean_kmh':'wind'})
output(day[['location_key','city','date','year','pm25','rain','temperature','wind','has_weather','jitter']],'daily')
annual=pd.read_csv(P/'location_annual.csv');annual=annual[annual.include_in_city_comparisons].copy();annual['city']=annual.location_key.map(names);annual=annual.rename(columns={'pm25_mean_ugm3':'pm25','air_latitude':'latitude','air_longitude':'longitude'})
output(annual[['location_key','city','year','pm25','latitude','longitude']],'annual')
month=pd.read_csv(P/'location_monthly.csv');month=month[month.location_key.isin(keys)].copy();month['city']=month.location_key.map(names);month['year']=month.month.str[:4].astype(int);month['month_number']=month.month.str[5:7].astype(int);month['month_name']=pd.to_datetime(month.month).dt.strftime('%b');month['theta']=(month.month_number-1)*math.pi/6;month['theta_end']=month.month_number*math.pi/6;month['theta_mid']=(month.month_number-.5)*math.pi/6
month=month.rename(columns={'pm25_mean_ugm3':'pm25','precipitation_mm':'rain'});output(month[['location_key','city','year','month','month_number','month_name','pm25','rain','theta','theta_end','theta_mid']],'monthly')
national=pd.read_csv(P/'national_pollution_monthly.csv');national=national[(national.pollutant=='PM2.5')&national.concentration.notna()];output(national[['date','concentration']],'national')
who=pd.read_csv(P/'who_residence_annual.csv');output(who[who.residence_type.isin(['Urban','Rural'])][['year','residence_type','pm25_ugm3']],'who')
fire=pd.read_csv(P/'fire_points.csv');fire['year']=fire.date.str[:4].astype(int);output(fire,'fire-points')
fd=pd.read_csv(P/'fire_daily.csv');fd['year']=fd.date.str[:4].astype(int);output(fd[['date','year','detections']],'fire-daily')
fs=pd.read_csv(P/'fire_state_annual.csv');output(fs,'fire-states')
def clockwise_geo(obj):
    # D3/Vega spherical projections expect clockwise exterior rings (< hemisphere).
    obj=copy.deepcopy(obj)
    for f in obj['features']:
        geom=f['geometry'];parts=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        for poly in parts:
            for i,ring in enumerate(poly):
                signed=sum(ring[j-1][0]*ring[j][1]-ring[j][0]*ring[j-1][1] for j in range(len(ring)))
                if (i==0 and signed>0) or (i>0 and signed<0):ring.reverse()
    return obj
states=clockwise_geo(json.loads((P/'malaysia_states.geojson').read_text()));bins=clockwise_geo(json.loads((P/'fire_spatial_bins.geojson').read_text()))
(D/'states.geojson').write_text(json.dumps(states,separators=(',',':')))
(D/'fire-bins.geojson').write_text(json.dumps(bins,separators=(',',':')))

GREEN='#287566';ORANGE='#b86038';BLUE='#527da2';GRID='#e3e7e1';CITY_COLORS=['#287566','#b86038','#527da2','#967544','#796899','#579189','#9e5572','#657940']
def data(name):
    return {'url':'data/site/'+name+'.csv','format':formats[name]} if name in formats else {'url':'data/site/'+name+'.json'}
def tip(field,title=None,typ='quantitative',fmt=None):
    t={'field':field,'type':typ,'title':title or field}
    if fmt:t['format']=fmt
    return t
pm=tip('pm25','PM2.5 (µg/m³)',fmt='.1f');ct=tip('city','Location','nominal');dt=tip('date','Date','temporal','%d %b %Y')
Y={'name':'selectedYear','value':2025};C={'name':'selectedCity','value':'L00'}
yearfilter={'filter':'datum.year == selectedYear'}
cityfilter={'filter':'datum.location_key == selectedCity'}
config={'background':'transparent','font':'Arial','view':{'stroke':None},'axis':{'labelColor':'#58675e','titleColor':'#45564a','labelFontSize':11,'titleFontSize':11,'titlePadding':12,'domain':False,'tickColor':GRID,'gridColor':GRID,'labelLimit':130},'legend':{'labelColor':'#58675e','titleColor':'#45564a','titleFontSize':11,'labelFontSize':11,'orient':'bottom','direction':'horizontal'},'range':{'category':CITY_COLORS},'title':{'color':'#203c30'}}
def save(name,spec,height=300):
    spec={'$schema':'https://vega.github.io/schema/vega-lite/v5.json','description':name.replace('-',' '),'width':'container','height':height,'autosize':{'type':'fit','contains':'padding'},'config':config,**spec}
    (S/(name+'.json')).write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
save('01-national',{'data':data('national'),'layer':[{'mark':{'type':'line','color':GREEN,'strokeWidth':2.5,'point':{'size':13}},'encoding':{'x':{'field':'date','type':'temporal','title':None,'axis':{'format':'%Y','tickCount':7}},'y':{'field':'concentration','type':'quantitative','title':'PM2.5 (µg/m³)','scale':{'zero':True}},'tooltip':[dt,tip('concentration','Monthly PM2.5 (µg/m³)',fmt='.2f')]}},{'transform':[{'filter':"year(toDate(datum.date)) == 2019 && month(toDate(datum.date)) == 8"}],'mark':{'type':'point','filled':True,'color':ORANGE,'size':80},'encoding':{'x':{'field':'date','type':'temporal'},'y':{'field':'concentration','type':'quantitative'}}}]})
save('02-residence',{'data':data('who'),'mark':{'type':'bar','cornerRadiusTopLeft':2,'cornerRadiusTopRight':2},'encoding':{'x':{'field':'year','type':'ordinal','title':None,'axis':{'labelAngle':0}},'xOffset':{'field':'residence_type'},'y':{'field':'pm25_ugm3','type':'quantitative','title':'Annual PM2.5 (µg/m³)'},'color':{'field':'residence_type','type':'nominal','title':None,'scale':{'domain':['Urban','Rural'],'range':[GREEN,'#b2c7a0']}},'tooltip':[tip('year','Year','ordinal'),tip('residence_type','Residence','nominal'),tip('pm25_ugm3','PM2.5 (µg/m³)',fmt='.2f')]}})
save('03-slope',{'data':data('annual'),'params':[C],'mark':{'type':'line','point':{'filled':True,'size':60},'strokeWidth':2},'encoding':{'x':{'field':'year','type':'ordinal','title':None,'axis':{'labelAngle':0}},'y':{'field':'pm25','type':'quantitative','title':'Annual PM2.5 (µg/m³)','scale':{'domain':[0,42]}},'detail':{'field':'city'},'color':{'field':'city','type':'nominal','title':None,'scale':{'domain':cities,'range':CITY_COLORS},'legend':None},'opacity':{'condition':{'test':'datum.location_key == selectedCity','value':1},'value':.35},'tooltip':[ct,tip('year','Year','ordinal'),pm]}})
basemap={'data':{'url':'data/site/states.geojson','format':{'type':'json','property':'features'}},'mark':{'type':'geoshape','fill':'#e4ebe1','stroke':'#a2b5a6','strokeWidth':.7}}
projection={'type':'mercator'}
save('04-location-map',{'params':[Y],'projection':projection,'layer':[basemap,{'data':data('annual'),'transform':[yearfilter],'mark':{'type':'circle','color':GREEN,'opacity':.72,'stroke':'#fff','strokeWidth':1.5},'encoding':{'longitude':{'field':'longitude','type':'quantitative'},'latitude':{'field':'latitude','type':'quantitative'},'size':{'field':'pm25','type':'quantitative','title':'PM2.5 (µg/m³)','scale':{'domain':[0,42],'range':[0,1400]}},'tooltip':[ct,tip('year','Year','ordinal'),pm]}}]},350)
save('05-heatmap',{'data':data('monthly'),'params':[Y],'transform':[yearfilter],'mark':{'type':'rect','stroke':'#fff','strokeWidth':2,'cornerRadius':2},'encoding':{'x':{'field':'month_name','type':'ordinal','sort':['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],'title':None,'axis':{'labelAngle':0}},'y':{'field':'city','type':'nominal','sort':cities,'title':None},'color':{'field':'pm25','type':'quantitative','title':'PM2.5 (µg/m³)','scale':{'domain':[0,65],'range':['#edf1df','#89b291','#1a6355']}},'tooltip':[ct,tip('month','Month','temporal','%b %Y'),pm]}},310)
save('06-jitter',{'data':data('daily'),'params':[Y],'transform':[yearfilter],'mark':{'type':'circle','size':11,'opacity':.3,'color':GREEN},'encoding':{'x':{'field':'city','type':'nominal','sort':cities,'title':None,'axis':{'labelAngle':-32,'labelLimit':125}},'xOffset':{'field':'jitter','type':'quantitative','scale':{'domain':[-.5,.5]}},'y':{'field':'pm25','type':'quantitative','title':'Daily PM2.5 (µg/m³)','scale':{'domain':[0,140]}},'tooltip':[ct,dt,pm]}},350)
save('07-weather',{'data':data('daily'),'params':[Y,C],'transform':[yearfilter,cityfilter,{'filter':'datum.has_weather'}],'mark':{'type':'circle','size':42,'opacity':.5,'color':BLUE},'encoding':{'x':{'field':'rain','type':'quantitative','title':'Daily precipitation (mm)','scale':{'zero':True}},'y':{'field':'pm25','type':'quantitative','title':'Daily PM2.5 (µg/m³)','scale':{'domain':[0,140]}},'tooltip':[ct,dt,pm,tip('rain','Precipitation (mm)',fmt='.1f'),tip('wind','10 m wind (km/h)',fmt='.1f')]}})
save('08-radial',{'data':data('monthly'),'params':[Y,C],'transform':[yearfilter,cityfilter,{'filter':'isValid(datum.rain)'},{'calculate':'20 + datum.rain / 1200 * max(30, min(width, height) / 2 - 60)', 'as':'bar_radius'}],'layer':[{'mark':{'type':'arc','innerRadius':20,'padAngle':.025,'color':BLUE},'encoding':{'theta':{'field':'theta','type':'quantitative','scale':None},'theta2':{'field':'theta_end'},'radius':{'field':'bar_radius','type':'quantitative','scale':None},'tooltip':[ct,tip('month','Month','temporal','%b %Y'),tip('rain','Precipitation (mm)',fmt='.1f')]}},{'mark':{'type':'text','radius':{'expr':'min(width, height) / 2 - 16'},'fontSize':11,'color':'#58675e'},'encoding':{'theta':{'field':'theta_mid','type':'quantitative','scale':None},'text':{'field':'month_name'}}}]},320)
save('09-fire-timeline',{'data':data('fire-daily'),'params':[Y,{'name':'episode','select':{'type':'interval','encodings':['x']}}],'transform':[yearfilter],'mark':{'type':'bar','color':ORANGE},'encoding':{'x':{'field':'date','type':'temporal','title':None,'axis':{'format':'%b','tickCount':12}},'y':{'field':'detections','type':'quantitative','title':'Detections / day'},'tooltip':[dt,tip('detections','Hotspot detections',fmt=',d')]}},220)
# Flatten state properties and attach both year metrics so the choropleth has a shared domain.
for f in states['features']:
    for yr in [2024,2025]:
        row=fs[(fs.state_code==f['properties']['state_code'])&(fs.year==yr)].iloc[0]
        f['properties']['density_'+str(yr)]=round(row.detections_per_1000_km2,3)
        f['properties']['count_'+str(yr)]=int(row.detections)
(D/'states.geojson').write_text(json.dumps(states,separators=(',',':')))
save('10-state-map',{'params':[Y],'data':{'url':'data/site/states.geojson','format':{'type':'json','property':'features'}},'transform':[{'calculate':"datum.properties['density_' + selectedYear]",'as':'density'},{'calculate':"datum.properties['count_' + selectedYear]",'as':'count'}],'projection':projection,'mark':{'type':'geoshape','stroke':'#fff','strokeWidth':.8},'encoding':{'color':{'field':'density','type':'quantitative','title':'Detections / 1,000 km²','scale':{'domain':[0,float(fs.detections_per_1000_km2.max())],'range':['#f5edda','#dba174','#a24925']}},'tooltip':[tip('properties.state_name','State','nominal'),tip('count','Detections',fmt=',d'),tip('density','Detections / 1,000 km²',fmt='.1f')]}},320)
save('11-hotspot-map',{'params':[Y,{'name':'episodeStart','value':'2025-01-01'},{'name':'episodeEnd','value':'2025-12-31'}],'projection':projection,'layer':[basemap,{'data':data('fire-points'),'transform':[yearfilter,{'filter':'toDate(datum.date) >= toDate(episodeStart) && toDate(datum.date) <= toDate(episodeEnd)'}],'mark':{'type':'circle','size':10,'opacity':.5,'color':ORANGE},'encoding':{'longitude':{'field':'longitude','type':'quantitative'},'latitude':{'field':'latitude','type':'quantitative'},'tooltip':[dt,tip('frp_mw','Radiative power (MW)',fmt='.1f'),tip('confidence','Confidence code','nominal'),tip('state_code','State code','nominal')]}}]},340)
save('12-bin-map',{'params':[Y],'projection':projection,'layer':[basemap,{'data':{'url':'data/site/fire-bins.geojson','format':{'type':'json','property':'features'}},'transform':[{'filter':'datum.properties.year == selectedYear'}],'mark':{'type':'geoshape','stroke':'#fff','strokeWidth':.25},'encoding':{'color':{'field':'properties.detections','type':'quantitative','title':'Detections / cell','scale':{'type':'sqrt','domain':[0,max(f['properties']['detections'] for f in bins['features'])],'range':['#f4dec3','#a24925']}},'tooltip':[tip('properties.year','Year','ordinal'),tip('properties.detections','Detections in cell',fmt=',d')]}}]},320)

# Keep annotations in the generator so rebuilding preserves them.
national_path=S/'01-national.json'
national_spec=json.loads(national_path.read_text(encoding='utf-8'))
peak_label=copy.deepcopy(national_spec['layer'][1])
peak_label['mark']={'type':'text','align':'left','dx':9,'dy':-10,'color':ORANGE,'fontSize':11}
peak_label['encoding']['text']={'value':'Sep 2019: 52.86'}
national_spec['layer'].append(peak_label)
national_path.write_text(json.dumps(national_spec,ensure_ascii=False,indent=2),encoding='utf-8')
slope_path=S/'03-slope.json'
slope_spec=json.loads(slope_path.read_text(encoding='utf-8'))
slope_marks={'mark':slope_spec.pop('mark'),'encoding':slope_spec.pop('encoding')}
slope_labels={'transform':[cityfilter], 'mark':{'type':'text','dy':-14,'fontSize':12,'fontWeight':'bold','color':GREEN},'encoding':{'x':{'field':'year','type':'ordinal'},'y':{'field':'pm25','type':'quantitative'},'text':{'field':'pm25','type':'quantitative','format':'.2f'}}}
slope_spec['layer']=[slope_marks,slope_labels]
slope_spec['height']=390
slope_marks['encoding']['color']['legend']={'title':'Location','orient':'bottom','columns':2,'labelFontSize':12,'labelLimit':150,'symbolOpacity':1,'rowPadding':7}
slope_labels['mark'].pop('color')
slope_labels['encoding']['color']=copy.deepcopy(slope_marks['encoding']['color'])
slope_path.write_text(json.dumps(slope_spec,ensure_ascii=False,indent=2),encoding='utf-8')

radial_path=S/'08-radial.json'
radial_spec=json.loads(radial_path.read_text(encoding='utf-8'))
radial_transforms=radial_spec.pop('transform')
bars,months=radial_spec['layer']
bars['transform']=radial_transforms
months['transform']=radial_transforms
bars['mark'].update({'stroke':'#fffef9','strokeWidth':1})
months['mark']['fontSize']=12
rings={'data':{'values':[{'tick':v,'label':f'{v:,} mm'} for v in [0,400,800,1200]]},'transform':[{'calculate':'20 + datum.tick / 1200 * max(30, min(width, height) / 2 - 60)','as':'guide_radius'}],'mark':{'type':'arc','fill':None,'stroke':'#aab8b0','strokeWidth':1,'innerRadius':0},'encoding':{'theta':{'value':0},'theta2':{'value':2*math.pi},'radius':{'field':'guide_radius','type':'quantitative','scale':None,'stack':None}}}
ring_labels=copy.deepcopy(rings)
ring_labels['mark']={'type':'text','align':'left','dx':3,'dy':-5,'fontSize':10,'color':'#45564a'}
ring_labels['encoding']={'theta':{'value':0},'radius':{'field':'guide_radius','type':'quantitative','scale':None,'stack':None},'text':{'field':'label'}}
radial_spec['layer']=[rings,bars,months,ring_labels]
radial_path.write_text(json.dumps(radial_spec,ensure_ascii=False,indent=2),encoding='utf-8')

stats={'namedLocations':len(loc),'weatherLocations':int(loc.weather_source_id.notna().sum()),'dailyRecords':len(day),'nationalPeak':{'month':'September 2019','value':52.86},'annual':annual[['city','year','pm25']].to_dict('records'),'fireTotals':{str(int(k)):int(v) for k,v in fs.groupby('year').detections.sum().items()},'cities':[{'key':r.location_key,'name':r.city,'weather':bool(pd.notna(r.weather_source_id))} for r in loc.itertuples()]}
(D/'summary.json').write_text(json.dumps(stats,indent=2))
print('Built 12 specifications. Browser data:',sum(p.stat().st_size for p in D.iterdir()),'bytes')
