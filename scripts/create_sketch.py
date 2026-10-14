from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, math, random

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'sketch';OUT.mkdir(parents=True,exist_ok=True)
W,H=1800,2546
im=Image.new('RGB',(W,H),'#fffdf7');d=ImageDraw.Draw(im)
INK='#29352f';MUTED='#65716a';GREEN='#3c7660';FAINT='#e4e9df';ORANGE='#bd7246'
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/arial'+('bd' if bold else '')+'.ttf',size)
def text(x,y,s,size=24,color=INK,bold=False):d.text((x,y),s,font=font(size,bold),fill=color)
def line(points,fill=INK,width=3):d.line(points,fill=fill,width=width)
def box(rect,fill=None,outline=INK,width=2):d.rectangle(rect,fill=fill,outline=outline,width=width)
def wrap(x,y,s,width,size=22,color=MUTED):
 words=s.split();out='';yy=y
 for word in words:
  candidate=(out+' '+word).strip()
  if d.textlength(candidate,font=font(size))>width and out:text(x,yy,out,size,color);yy+=size+7;out=word
  else:out=candidate
 if out:text(x,yy,out,size,color)
 return yy+size+7

geo=json.loads((ROOT/'data/prepared/malaysia_states.geojson').read_text())
def map_shape(x,y,w,h,kind):
 # Schematic regional frame using the supplied real state geometry.
 scale=min(w/22,h/7.5)
 def p(lon,lat):return (x+(lon-98)*scale,y+(8-lat)*scale)
 for i,f in enumerate(geo['features']):
  g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
  for poly in polys:
   coords=[p(a,b) for a,b,*_ in poly[0]]
   shade=['#e3ece2','#bccfbf','#93b69e','#649078'][i%4] if kind=='choropleth' else FAINT
   d.polygon(coords,fill=shade,outline=MUTED)
 if kind=='symbol':
  for lon,lat,r in [(101.7,3.1,12),(100.3,5.4,8),(103.8,1.5,10),(110.3,1.6,7),(114,4.4,9),(116.1,6,6)]:
   a,b=p(lon,lat);d.ellipse((a-r,b-r,a+r,b+r),fill=GREEN,outline=INK,width=1)
 if kind=='dot':
  rng=random.Random(7)
  for lon,lat in [(101.5,4),(110.8,2.2),(114.2,4.3)]:
   for _ in range(20):
    a,b=p(lon+rng.uniform(-.65,.65),lat+rng.uniform(-.35,.35));d.ellipse((a-2,b-2,a+2,b+2),fill=ORANGE)
 if kind=='bin':
  for lon,lat,n in [(101,4,3),(110.5,2.3,4),(114,4.4,2)]:
   for i in range(n):
    for j in range(2):
     a,b=p(lon+i*.35,lat+j*.35);d.rectangle((a,b,a+7,b+7),fill=[GREEN,ORANGE,MUTED][i%3])
 text(x,y+h-3,'Malaysia | schematic marks',16,MUTED)

def axes(x,y,w,h,xlabel,ylabel):
 line([(x,y),(x,y+h),(x+w,y+h)],MUTED,2)
 text(x+8,y-25,ylabel,17,MUTED)
 text(x+w//2-35,y+h+7,xlabel,17,MUTED)

def plot(kind,x,y,w,h):
 if kind in ['symbol','choropleth','dot','bin']:map_shape(x,y,w,h,kind);return
 if kind=='heat':
  text(x,y-23,'Location       Jan ... Dec, by year',17,MUTED)
  for r in range(6):
   text(x,y+r*25,'City '+str(r+1),15,MUTED)
   for c in range(12):
    a=x+70+c*(w-70)/12;b=y+r*25
    box((a,b,a+(w-70)/12-3,b+21),['#e3ece2','#bccfbf','#93b69e','#649078'][(r+c*3)%4],None)
  return
 if kind=='slope':
  text(x,y-23,'Annual mean PM2.5',17,MUTED)
  left,right=x+60,x+w-60
  line([(left,y),(left,y+h-30)],FAINT,2);line([(right,y),(right,y+h-30)],FAINT,2)
  for i,(a,b) in enumerate([(12,30),(37,18),(61,72),(82,61),(107,98)]):
   color=GREEN if b>a else ORANGE
   line([(left,y+a),(right,y+b)],color,3)
   for xx,yy in [(left,y+a),(right,y+b)]:d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=color)
  text(left-20,y+h-17,'2024',17,MUTED);text(right-20,y+h-17,'2025',17,MUTED)
  return
 if kind=='radial':
  cx,cy=x+w/2,y+h/2;rad=min(h/2-20,w/2)
  for f in [.33,.66,1]:d.ellipse((cx-rad*f,cy-rad*f,cx+rad*f,cy+rad*f),outline=FAINT,width=2)
  for i in range(12):
   a=i*math.pi/6-math.pi/2;r=rad*(.4+((i*7)%10)/16)
   outer=[(cx+r*math.cos(a+t/100),cy+r*math.sin(a+t/100)) for t in range(-19,20)]
   inner=[(cx+12*math.cos(a+t/100),cy+12*math.sin(a+t/100)) for t in range(19,-20,-1)]
   d.polygon(outer+inner,fill=GREEN)
  for label,dx,dy in [('Jan',-12,-rad-23),('Jul',-12,rad+2),('Oct',-rad-36,-8),('Apr',rad+8,-8)]:text(cx+dx,cy+dy,label,17)
  text(x,y+h-5,'Monthly rainfall (mm)',17,MUTED);return
 axes(x,y,w,h-30,'Time' if kind in ['line','timeline'] else 'PM2.5' if kind in ['hist','scatter'] else 'Year' if kind=='bars' else 'Location','Rainfall' if kind=='scatter' else 'Days' if kind=='hist' else 'Detections' if kind=='timeline' else 'PM2.5')
 hh=h-35
 if kind in ['line','timeline']:
  vals=[.3,.32,.55,.28,.35,.85,.4,.2,.34,.5,.3,.22]
  if kind=='line':line([(x+i*w/11,y+hh*(1-v)) for i,v in enumerate(vals)],GREEN,4)
  else:
   for i,v in enumerate(vals):box((x+i*w/12+4,y+hh*(1-v),x+(i+1)*w/12-4,y+hh),GREEN,None)
 elif kind in ['hist','bars']:
  vals=[.1,.3,.8,1,.7,.35,.15,.06] if kind=='hist' else [.6,.4,.7,.5,.8,.55]
  for i,v in enumerate(vals):
   gap=2 if kind=='hist' else 12;box((x+i*w/len(vals)+gap,y+hh*(1-v),x+(i+1)*w/len(vals)-gap,y+hh),GREEN if i%2==0 or kind=='hist' else '#a5bda8',None)
 elif kind=='scatter':
  rng=random.Random(4)
  for _ in range(50):
   a=rng.uniform(.03,.97);b=rng.uniform(.03,.95);xx=x+a*w;yy=y+b*hh;d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=GREEN)
 elif kind=='jitter':
  rng=random.Random(12)
  for i in range(5):
   for _ in range(30):
    a=x+35+i*w/5+rng.uniform(-18,18);b=y+max(3,min(hh-3,rng.gauss(hh*(.4+i*.065),22)))
    d.ellipse((a-2,b-2,a+2,b+2),fill=GREEN)

text(80,58,'SKETCH DRAFT / FIT3179',24,GREEN,True)
text(80,104,'THE AIR WE SHARE',66,INK,True)
text(82,183,'PM2.5 across Malaysia: place, weather and fire hotspots',29)
text(82,231,'Main comparison: 2024-2025  |  National context: earlier years',23,MUTED)
text(82,270,'12 charts   /   4 distinct map idioms   /   8 advanced idioms',25,GREEN,True)
line([(80,316),(1720,316)],GREEN,3)
text(82,334,'Intro: explain PM2.5 in plain language; distinguish model estimates from observations.',22)
text(82,369,'Planned controls: year selector + location selector. Keep all four sections on one page.',22,MUTED)

sections=[
 ('01  /  THE BIG PICTURE','Introduce national context, then compare changes across locations.',[
 ('National change over time','STANDARD','line','Line chart | national monthly PM2.5','Hover: month + concentration. Mark notable peaks after analysis.'),
 ('Urban and rural exposure','STANDARD','bars','Grouped bars | annual WHO estimates','Own year selector (2017-2023). Compare urban and rural; do not stack.'),
 ('How did locations change?','ADVANCED 1','slope','Slope chart | annual PM2.5, 2024 to 2025','One line per location. Highlight a location; label both endpoint values.')]),
 ('02  /  HOW DO LOCATIONS DIFFER?','Compare eight named locations; omit the unconfirmed location.',[
 ('Where is PM2.5 higher?','MAP 1 / ADVANCED 2','symbol','Proportional-symbol map | annual PM2.5','Circle area = concentration. Year selector; hover for model-grid value.'),
 ('When does pollution rise?','ADVANCED 3','heat','Heatmap | location by month','Colour = monthly mean. Year selector and a shared colour legend.'),
 ('Typical days and extremes','ADVANCED 4','jitter','Jitter plot | daily PM2.5 by location','One dot per day. Jitter horizontally only; hover for date and value.')]),
 ('03  /  WEATHER AND POLLUTION','Investigate relationships for seven locations with matching weather.',[
 ('Rainfall and PM2.5','STANDARD','scatter','Scatterplot | paired daily values','Location selector. Each point is a day; association is not causation.'),
 ('When are the wetter months?','ADVANCED 5','radial','Radial bar chart | monthly rainfall','Location + year selectors. Radial length = rainfall; months run clockwise.'),
 ('When do hotspots peak?','STANDARD','timeline','Column timeline | daily hotspot detections','Brush a date range to select the episode shown in map 3 below.')]),
 ('04  /  THE GEOGRAPHY OF HOTSPOTS','Three different scales: state rates, an episode, and regional clusters.',[
 ('Which states have more detections?','MAP 2 / ADVANCED 6','choropleth','Choropleth | detections per 1,000 km2','Year selector. Colour encodes density, not state PM2.5.'),
 ('Where was the selected episode?','MAP 3 / ADVANCED 7','dot','Dot map | individual hotspot detections','Linked date range. Zoom to an episode; dots are not distinct fires.'),
 ('Where are the broader clusters?','MAP 4 / ADVANCED 8','bin','Spatial-bin map | counts per 0.25-degree cell','Year selector. Colour = counts per cell; no invented pollution surface.')])]

top=425;cw=530;ch=375
for si,(heading,sub,charts) in enumerate(sections):
 sy=top+si*480
 text(80,sy,heading,29,GREEN,True);text(80,sy+42,sub,22,MUTED)
 for ci,(title,badge,kind,caption,note) in enumerate(charts):
  x=80+ci*555;y=sy+80
  box((x,y,x+cw,y+ch),None,MUTED,2)
  text(x+16,y+12,f'{si*3+ci+1:02d}  {badge}',19,GREEN,True)
  wrap(x+16,y+42,title,cw-32,24,INK)
  plot(kind,x+42,y+110,cw-80,155)
  text(x+16,y+289,caption,18,INK,True)
  wrap(x+16,y+317,note,cw-32,18,MUTED)

line([(80,2362),(1720,2362)],GREEN,3)
text(80,2380,'FOOTER: sources + methods + author + date + AI acknowledgement',23,INK,True)
text(80,2422,'Illustrative chart shapes only: no plotted values or visual patterns are findings.',22,ORANGE,True)
text(80,2460,'Planning guide only. Redraw your final A4 sketch by hand and discuss it with your tutor.',22,MUTED)
im.save(OUT/'air-quality-sketch-draft.png',dpi=(218,218))
print(OUT/'air-quality-sketch-draft.png')

