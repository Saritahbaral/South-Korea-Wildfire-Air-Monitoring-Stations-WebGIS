"""Package saved all-pair wind results and best-five PM outputs for the WebGIS.
Run locally: py build_data.py
This reads existing results only. It does not calculate PM, wind or station selection.
The national inventory and event labels are retained in inventory_seed.json.
"""
from pathlib import Path
import csv, hashlib, json, math, shutil
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
WIND=ROOT/'04_KMA_Downwind_Analysis'/'Results_All_Spatial_Pairs'
PM=ROOT/'06_PM_Timeseries_Graphs'/'Results_Best5_Graphs_and_Summary_Tables'
def read(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(v):
 try:
  n=float(v);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None
def flag(v):return str(v).lower()=='true'
def key(r):return (r['Event_ID'],r['Station_Code'])
def write_csv(path,rows):
 if not rows:return
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 seed=json.loads((OUT/'inventory_seed.json').read_text(encoding='utf-8'))
 names=json.loads((OUT/'station_names_en.json').read_text(encoding='utf-8'))
 summary=read(WIND/'All_Events_Downwind_Station_Summary.csv')
 best=read(PM/'Best5_Selected_Stations.csv');audit=read(PM/'Best5_Selection_Audit.csv')
 quality={r['Event_ID']:r for r in read(WIND/'KMA_AWS_Event_Quality.csv')}
 pm=read(PM/'PM_Summary_Table.csv')
 chosen={key(r):r for r in best};allowed={key(r):r for r in audit}
 if len({key(r) for r in summary})!=len(summary):raise ValueError('Duplicate wind summary keys')
 if not set(chosen).issubset(allowed) or not set(allowed).issubset({key(r) for r in summary}):raise ValueError('Inconsistent selection inputs')
 if len(chosen)!=len(best):raise ValueError('Duplicate best-five pairs')
 evidence={(r['Event'],r['Station code'],r['Window'],r['Pollutant']):r for r in pm}
 assets=OUT/'assets';downloads=assets/'downloads';downloads.mkdir(parents=True,exist_ok=True)
 sources=[]
 def copy(src,dst):
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  sources.append({'path':str(src.relative_to(ROOT)), 'bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'packagedPath':str(dst.relative_to(OUT))})
 for f in WIND.glob('*.csv'):copy(f,downloads/f.name)
 for f in ['Best5_Selected_Stations.csv','Best5_Selection_Audit.csv','PM_Summary_Table.csv','PM_Summary_Tables.xlsx']:copy(PM/f,downloads/f)
 copy(PM/'Best5_All_Events_PM_Anomalies.pdf',assets/'All_Wildfires_PM_Anomalies.pdf')
 table_dir=PM/'PM_Summary_Tables'
 for f in ['All_Events_PM_Summary_Tables.pdf','All_Events_PM_Summary_Tables.xlsx']:
  copy(table_dir/f,assets/'tables'/f)
 # Copy the saved table cells into readable interface tables without recomputing statistics.
 from openpyxl import load_workbook
 workbook=load_workbook(assets/'tables'/'All_Events_PM_Summary_Tables.xlsx',data_only=True)
 cells={}
 for sheet in workbook:
  cells[sheet.title]=[['' if v is None else str(v) for v in row[:13]] for row in list(sheet.values)[4:] if len(row)>4 and row[4] in ['PM₂.₅','PM₁₀']]
 (assets/'tables'/'table_cells.json').write_text(json.dumps(cells,ensure_ascii=False),encoding='utf-8')
 (OUT/'table_cells.js').write_text('window.PM_TABLE_CELLS = '+json.dumps(cells,ensure_ascii=False)+';\n',encoding='utf-8')
 exposure={}
 for r in read(WIND/'All_Events_Hourly_Station_Exposure.csv'):exposure.setdefault(key(r),{})[r['Timestamp']]=r['Exposure_Sector']
 winds={}
 for r in read(WIND/'All_Events_Hourly_KMA_AWS_Wind.csv'):
  winds.setdefault(r['Event_ID'],[]).append({'time':r['Timestamp'],'speed':num(r['Vector_Mean_Speed_m_s']),'toward':num(r['Plume_Toward_deg']),'status':r['Wind_Status'],'reporting':num(r['Sources_Reporting']),'sources':r['KMA_AWS_Sources']})
 events=[]
 for original in seed['events']:
  e=original.copy();eid=e['id'];rows=[r for r in summary if r['Event_ID']==eid]
  if not rows:raise ValueError('No spatial pairs for '+eid)
  r=rows[0];e.update(lat=num(r['Wildfire_Latitude']),lon=num(r['Wildfire_Longitude']),start=r['Fire_Start'],end=r['Fire_End'],windowStart=r['Analysis_Window_Start'],windowEnd=r['Analysis_Window_End'],windCoverage=num(quality[eid]['Wind_Coverage_Percent']),windQuality=quality[eid]['Overall_Quality_Status'])
  e['stations']=[];e['wind']=sorted(winds[eid],key=lambda x:x['time'])
  for r in sorted(rows,key=lambda r:(float(r['Distance_km']),r['Station_Code'])):
   pair=key(r);b=chosen.get(pair,{});a=allowed.get(pair,{})
   s={'code':r['Station_Code'],'name':r['AQ_Station_Name'],'lat':num(r['Station_Latitude']),'lon':num(r['Station_Longitude']),'distance':num(r['Distance_km']), 'type':r['측정소구분'],'province':r['시도'],'city':r['도시'],'address':r['주소'],
      'eligible':flag(r['PM_Meets_75_Percent']),'pmSelected':bool(a),'analyzed':bool(b),'initialSelected':bool(b),'selectionRole':b.get('Best5_Selection_Role',''),'selectionRank':num(b.get('Best5_Rank')),'category':a.get('Selection_Category',''), 'availability':r['PM_Observation_Availability_Status'],'historicalOperation':r['Historical_Operation_Status'],'completeness':num(r['PM_Paired_Completeness_Percent']),'downwindHours':num(r['Downwind_Hours']),'downwindPercent':num(r['Downwind_Percent_of_Noncalm']),'baselineQuality':'Not in final selected stations','baseline25':None,'baseline10':None,'anomaly25':None,'anomaly10':None,'exposure':exposure.get(pair,{}),'exclusion':'','nameMismatch':False,'metadataName':r['AQ_Station_Name']}
   s.update(names.get(s['code'],{'nameEn':s['name'],'nameEnSource':'Source station name'}))
   for pol,suffix in [('PM2.5','25'),('PM10','10')]:
    arow=evidence.get((eid,s['code'],'Active fire',pol))
    if b and not arow:raise ValueError('Missing best-five PM summary: '+str(pair))
    if arow:s['baseline'+suffix]=num(arow['Baseline mean']);s['anomaly'+suffix]=num(arow['Mean anomaly']);s['baselineQuality']=arow['Baseline status']
   e['stations'].append(s)
  if sum(s['analyzed'] for s in e['stations'])>5:raise ValueError('More than five final selected stations')
  copy(PM/'Graphs'/eid/(eid+'_PM_Anomalies.png'),assets/(eid+'_PM_Anomalies.png'))
  copy(table_dir/'Event_PDFs'/(eid+'_PM_Summary_Table.pdf'),assets/'tables'/(eid+'_PM_Summary_Table.pdf'))
  e['graphs']={'anomaly':'assets/'+eid+'_PM_Anomalies.png'}
  e['tablePdf']='assets/tables/'+eid+'_PM_Summary_Table.pdf'
  e['tablePreview']='assets/tables/'+eid+'_PM_Summary_Table.png'
  write_csv(downloads/(eid+'_Stations.csv'),[{'Station code':s['code'],'Station':s['nameEn'],'Korean name':s['name'],'Distance km':s['distance'],'PM availability':s['availability'],'Paired completeness %':s['completeness'],'PM selected':s['pmSelected'],'Final selected stations':s['analyzed'],'Selection role':s['selectionRole'],'Downwind hours':s['downwindHours'],'Downwind noncalm %':s['downwindPercent'],'Baseline status':s['baselineQuality'],'Baseline PM2.5':s['baseline25'],'Baseline PM10':s['baseline10'],'Active anomaly PM2.5':s['anomaly25'],'Active anomaly PM10':s['anomaly10']} for s in e['stations']])
  write_csv(downloads/(eid+'_PM_Summary.csv'),[r for r in pm if r['Event']==eid])
  events.append(e)
 counts={'events':len(events),'nationalStations':len(seed['nationalStations']),'uniqueStations':len({s['code'] for e in events for s in e['stations']}),'candidateRelationships':len(summary),'eligibleRelationships':sum(s['eligible'] for e in events for s in e['stations']),'pmSelectedRelationships':len(allowed),'analyzedRelationships':len(best)}
 notes=[
  'Saved historical research outputs; all timestamps are KST. The viewer does not recalculate wind, PM or selection.',
  'The national inventory of 688 stations and event location labels are retained from the uploaded platform. Event and station coordinates, distances and dates for the 241 spatial pairs come from the updated wind summary.',
  'Candidates are within 50 km, without a provincial boundary filter. PM completeness passes at >=75% paired observations over the screening window. No observations found is not proof that a station did not operate historically.',
  'The saved PM analysis pool contains 184 pairs: paired completeness >=75% AND (distance <=25 km OR >=5 downwind hours), within 50 km.',
  'The final selected stations contains 46 pairs: two nearest eligible pairs, then up to three other pairs by descending downwind hours. Ties use distance, completeness and station code as documented in the saved audit. Events 1 and 2 retain three pairs each; all others retain five.',
  'Detailed PM values in this package cover the 46 final selected pairs only. Other PM-selected pairs have no detailed baseline or anomaly attached here; this does not imply their analysis was not performed.',
  'Baseline is each pollutant\'s available seven-day prefire mean; anomaly is observation minus baseline. Baseline PASS requires >=75% paired prefire hours; REVIEW is retained. Missing data are not interpolated.',
  'Wind uses up to three qualifying KMA/AWS sources within 50 km, vector averaged. Downwind is within 45 degrees of transport direction, excluding resultant speeds below 0.5 m/s. Percentages use noncalm hours. Hourly alignment is available for all 241 pairs, including pairs lacking PM.',
  'Fire markers use officially disclosed ignition coordinates (Korea Forest Service disclosure 17661143); source datum and accuracy are unspecified. EPSG:4326 remains the project mapping convention. Markers are not burn perimeters. Original project event times are retained.',
  'Wind alignment, proximity and positive PM anomalies do not establish smoke arrival or wildfire causation. Map filters change display only.',
  'Graph images and PDF/Excel tables are copied unchanged from the supplied latest outputs. Background tiles load online from OpenStreetMap or Esri; the research results are bundled locally.'
 ]
 d={'events':events,'nationalStations':seed['nationalStations'],'sources':sources,'counts':counts,'notes':notes}
 (OUT/'data.js').write_text('window.WILDFIRE_DATA = '+json.dumps(d,ensure_ascii=False,allow_nan=False,separators=(',',':'))+';\n',encoding='utf-8')
 (OUT/'source_manifest.json').write_text(json.dumps({'sources':sources,'retainedInventoryProvenance':seed['inventorySources'],'counts':counts},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(counts));print('Packaged saved results only; no analysis performed.')
if __name__=='__main__':main()
