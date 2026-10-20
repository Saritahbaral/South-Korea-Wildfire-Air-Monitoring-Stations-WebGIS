'use strict';
(() => {
const D=window.WILDFIRE_DATA, $=id=>document.getElementById(id);
if(!D?.events?.length||!window.L){document.querySelector('main').innerHTML='<p class="empty">Map assets are unavailable. Keep data.js and vendor beside index.html.</p>';return;}
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(x,n=1)=>x===null||x===undefined||!Number.isFinite(Number(x))?'—':Number(x).toLocaleString('en-US',{maximumFractionDigits:n,minimumFractionDigits:n});
const date=x=>(x||'').slice(0,16); // The archive stores KST timestamps as strings.
const category=x=>({DOWNWIND_AND_VERY_CLOSE:'Within 25 km + ≥5 downwind hours',DOWNWIND:'≥5 downwind hours',VERY_CLOSE:'Within 25 km'}[x]||'Not in PM analysis');
const sector=x=>({DOWNWIND:'Downwind',UPWIND:'Upwind',CROSSWIND:'Crosswind',CALM:'Calm',MISSING:'Missing wind'}[x]||x||'Not assessed');
const hasPosition=s=>Number.isFinite(s?.lat)&&Number.isFinite(s?.lon);
const stationTypes={'도시대기':'Urban','도로변대기':'Roadside','교외대기':'Suburban','국가배경':'Background','국가배경농도':'Background','항만':'Port','산단대기':'Industrial'};
const stationColors={'도시대기':'#2878b5','도로변대기':'#7b3294','교외대기':'#2ca25f','국가배경':'#d95f0e','국가배경농도':'#d95f0e','항만':'#008c95','산단대기':'#636363'};
const exposureColors={DOWNWIND:'#d76724',UPWIND:'#2878b5',CROSSWIND:'#7b539e',CALM:'#8494a2',MISSING:'#8494a2'};
let event=D.events[0],selectedCode=null,hour=0,tableExpanded=false;
const englishByCode=new Map(D.events.flatMap(e=>e.stations).filter(s=>s.nameEn&&s.nameEn!==s.name).map(s=>[s.code,s.nameEn]));
D.nationalStations.forEach(s=>{s.nameEn=englishByCode.get(s.code)||s.nameEn||s.name;});
const stationName=s=>s.nameEn||s.name;
const mapStationName=s=>stationName(s)!==s.name?`${stationName(s)} / ${s.name}`:s.name;
const lookup=new Map(D.nationalStations.map(s=>[s.code,s]));
const layer=()=> $('stationLayer').value;
const query=()=> $('stationSearch').value.trim().toLocaleLowerCase();
const matching=s=>!query()||[s.name,s.nameEn,s.code,s.address,s.province,s.city].join(' ').toLocaleLowerCase().includes(query());
const stations=()=>event.stations.filter(s=>s.distance<=Number($('distanceFilter').value)&&(layer()==='all'||layer()==='national'||layer()==='exposure'||(layer()==='eligible'?s.eligible:layer()==='pm'?s.pmSelected:s.analyzed))&&matching(s));
const national=()=>D.nationalStations.filter(matching);
const wind=()=>event.wind[hour]||null;
const map=L.map('map',{zoomControl:false,preferCanvas:true,scrollWheelZoom:true,doubleClickZoom:false}).setView([36.5,127.8],7);
const osmTiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
  attribution:'&copy; OpenStreetMap contributors',maxZoom:19,
}).addTo(map);
const esriTiles=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',{
  attribution:'Tiles &copy; Esri; sources: Esri, HERE, Garmin, USGS, Intermap, NRCan, Esri Japan, METI, &copy; OpenStreetMap contributors, GIS User Community',maxZoom:18,maxNativeZoom:18,
});
L.control.layers({'OpenStreetMap':osmTiles,'Esri World Street Map':esriTiles},null,{position:'topright'}).addTo(map);
L.control.scale({imperial:false,position:'bottomleft'}).addTo(map);
const fires=L.layerGroup().addTo(map), points=L.layerGroup().addTo(map), windOverlay=L.layerGroup().addTo(map);
function fit(entities){const valid=entities.filter(hasPosition);if(valid.length)map.fitBounds(L.latLngBounds(valid.map(s=>[s.lat,s.lon])).pad(.18),{maxZoom:12,animate:false});}
function fitAll(){fit([...D.events,...D.nationalStations]);}
function fitEvent(){fit([event,...event.stations.filter(s=>s.analyzed&&hasPosition(s))]);}
function showEvent(id){event=D.events.find(e=>e.id===id)||D.events[0];hour=0;selectedCode=null;tableExpanded=false;$('stationSearch').value='';$('eventSelect').value=event.id;render();fitEvent();}
function chooseStation(code){selectedCode=code;renderStation();renderTable();renderMap();}
function renderHeader(){
 $('eventEyebrow').textContent=`EVENT ${String(event.number).padStart(2,'0')} · ${event.start.slice(0,4)} · ${event.legacyId.replace('_',' ')} in legacy files`;
 $('eventName').textContent=event.name;$('eventKo').textContent=event.nameKo;
 $('burnedArea').textContent=num(event.area,2)+' ha';$('fireStart').textContent=date(event.start);$('fireEnd').textContent=date(event.end);
 $('analyzedCount').textContent=event.stations.filter(s=>s.analyzed).length+' final selected · '+event.stations.filter(s=>s.pmSelected).length+' PM pool';
 $('windCoverage').textContent=num(event.windCoverage,1)+'% · '+event.windQuality;
 document.querySelectorAll('.event-button').forEach(b=>{b.classList.toggle('active',b.dataset.event===event.id);b.setAttribute('aria-current',b.dataset.event===event.id?'true':'false');});
 $('coordinateWarning').textContent=event.precision+' · '+event.verification+'. Officially reported ignition point; source CRS/datum and accuracy unspecified.';
}
function renderStation(){
 const s=event.stations.find(s=>s.code===selectedCode),n=lookup.get(selectedCode);
 if(!s&&n){$('stationDetails').innerHTML=`<div class="station-name">${esc(stationName(n))}</div><p class="station-code">${esc(n.name)} · Station ${esc(n.code)}</p><span class="badge">${esc(stationTypes[n.type]||n.type)}</span><div class="detail-row"><span>Province / city</span><strong>${esc(n.province)} · ${esc(n.city)}</strong></div><div class="detail-row"><span>Address</span><strong>${esc(n.address)}</strong></div><div class="detail-row"><span>Coordinates</span><strong>${num(n.lat,5)}<br>${num(n.lon,5)}</strong></div><p class="secondary small">This station is in the national inventory. Detailed PM results are bundled only for the final selected stations.</p>`;return;}
 if(!s){$('stationDetails').innerHTML='<p class="empty">Select a station marker or a station in the event table to see its details.</p>';return;}
 const current=wind(),state=current?s.exposure[current.time]:null;
 $('stationDetails').innerHTML=`<div class="station-name">${esc(stationName(s))}</div><p class="station-code">${esc(s.name)} · ${esc(s.code)}</p><span class="badge">${esc(s.analyzed?'Final selected: '+s.selectionRole:s.pmSelected?'PM analysis pool':s.eligible?'Eligible station':'Completeness not met')}</span><div class="detail-row"><span>Distance from fire</span><strong>${num(s.distance)} km</strong></div><div class="detail-row"><span>Coordinates</span><strong>${num(s.lat,5)}<br>${num(s.lon,5)}</strong></div><div class="detail-row"><span>Current exposure</span><strong>${esc(sector(state))}</strong></div><div class="detail-row"><span>Baseline quality</span><strong>${esc(s.baselineQuality)}</strong></div><div class="detail-row"><span>PM availability</span><strong>${esc(s.availability)}</strong></div><div class="detail-row"><span>Paired completeness</span><strong>${num(s.completeness)}%</strong></div><div class="detail-row"><span>Downwind hours</span><strong>${num(s.downwindHours,0)}</strong></div><h4>7-day prefire mean · µg/m³</h4><div class="pm-stat"><div><small>PM2.5</small><strong>${num(s.baseline25)}</strong></div><div><small>PM10</small><strong>${num(s.baseline10)}</strong></div></div><h4>Active-fire mean anomaly · µg/m³</h4><div class="pm-stat"><div><small>PM2.5</small><strong>${num(s.anomaly25)}</strong></div><div><small>PM10</small><strong>${num(s.anomaly10)}</strong></div></div><p class="secondary small">${s.analyzed?'Anomalies are differences from the station baseline; they do not alone establish wildfire causation.':'Detailed PM values are bundled only for the final selected stations.'}</p>${s.exclusion?`<p class="source-warning">Selection note: ${esc(s.exclusion)}</p>`:''}${s.nameMismatch?`<p class="source-warning">Source name differs from station metadata (${esc(s.metadataName)}).</p>`:''}`;
}
function renderTable(){const base=stations(),list=layer()==='national'&&!tableExpanded&&!query()?base.filter(s=>s.analyzed):base,w=wind();$('tableCaption').textContent=list.length+' shown · '+event.stations.length+' assessed';$('toggleCandidates').hidden=layer()!=='national';$('toggleCandidates').textContent=tableExpanded?'Show final selected stations':'Show all '+event.stations.length+' spatial pairs';$('toggleCandidates').setAttribute('aria-expanded',String(tableExpanded));$('stationRows').innerHTML=list.length?list.map(s=>{const state=w?s.exposure[w.time]:null;return `<tr class="${s.code===selectedCode?'selected':''}"><td><button data-station="${esc(s.code)}">${esc(stationName(s))} <small>${esc(s.code)} · ${esc(s.name)}</small></button></td><td>${num(s.distance)} km</td><td>${esc(s.analyzed?'Final selected: '+s.selectionRole:s.pmSelected?'PM analysis pool':s.eligible?'Eligible station':'Completeness not met')}</td><td>${num(s.completeness)}%</td><td>${num(s.downwindHours,0)} h / ${s.downwindPercent===null?'—':num(s.downwindPercent)+'%'}</td><td><span class="sector ${['DOWNWIND','UPWIND'].includes(state)?state:''}">${esc(sector(state))}</span></td></tr>`;}).join(''):'<tr><td colspan="6" class="empty">No matching event candidates.</td></tr>';}
function renderWind(){const w=wind();$('windTime').max=Math.max(0,event.wind.length-1);$('windTime').value=hour;$('windTime').disabled=!event.wind.length;$('previousHour').disabled=hour===0;$('nextHour').disabled=hour>=event.wind.length-1;
 $('windTimestamp').textContent=w?date(w.time)+' KST':'No wind observations';$('windValue').textContent=w?`${num(w.speed,2)} m/s · ${w.status==='NONCALM'&&w.toward!==null?num(w.toward,0)+'° toward':w.status}`:'Wind unavailable';$('windSources').textContent=w?`${w.sources} · Reporting sources: ${num(w.reporting,0)}`:'';}
function destination(lat,lon,bearing,km){const R=6371,rad=bearing*Math.PI/180,a=lat*Math.PI/180,b=lon*Math.PI/180,d=km/R,al=Math.asin(Math.sin(a)*Math.cos(d)+Math.cos(a)*Math.sin(d)*Math.cos(rad)),bl=b+Math.atan2(Math.sin(rad)*Math.sin(d)*Math.cos(a),Math.cos(d)-Math.sin(a)*Math.sin(al));return [al*180/Math.PI,bl*180/Math.PI];}
function renderMap(){
 fires.clearLayers();points.clearLayers();windOverlay.clearLayers();
 for(const e of D.events){if(!hasPosition(e))continue;const active=e.id===event.id;
  const icon=L.divIcon({className:'fire-map-icon',html:`<span class="${active?'current':''}">${e.number}</span>`,iconSize:[34,34],iconAnchor:[17,17]});
  const marker=L.marker([e.lat,e.lon],{icon,title:`Event ${e.number} · ${e.name}`,zIndexOffset:active?2000:1000}).addTo(fires);
  marker.bindTooltip(`${e.number}`,{permanent:true,direction:e.number===2?'left':'right',className:'wildfire-number-label'});marker.bindPopup(`<b>Event ${e.number}: ${esc(e.name)}</b><br>${esc(e.nameKo)}<br>Start: ${esc(date(e.start))} KST<br>End: ${esc(date(e.end))} KST<br>Reported area: ${num(e.area,2)} ha`);marker.on('click',()=>{showEvent(e.id);fires.eachLayer(m=>{if(m.options.title===`Event ${e.number} · ${e.name}`)m.openPopup();});});
 }
 const showNational=layer()==='national',showExposure=['exposure','finalExposure'].includes(layer()),pool=showNational?national():stations();
 const container=showNational?L.markerClusterGroup({disableClusteringAtZoom:12,showCoverageOnHover:false,spiderfyOnMaxZoom:true,chunkedLoading:true}):L.layerGroup();
 L.circle([event.lat,event.lon],{radius:Number($('distanceFilter').value)*1000,color:'#d73027',weight:1,fillOpacity:.025,interactive:false}).addTo(windOverlay);
 const current=wind();
 for(const s of pool){if(!hasPosition(s))continue;const state=showExposure&&current?s.exposure[current.time]:null;
  let color=showExposure?(exposureColors[state]||exposureColors.MISSING):showNational?(stationColors[s.type]||'#636363'):(s.analyzed?'#0988b0':s.eligible?'#1c9f72':'#95a8b8');
  const marker=L.circleMarker([s.lat,s.lon],{radius:s.code===selectedCode?9:5.5,color:s.code===selectedCode?'#152f45':'white',weight:s.code===selectedCode?2.5:1.2,fillColor:color,fillOpacity:.95});
  marker.bindTooltip(`${esc(mapStationName(s))} (${esc(s.code)})${showNational?' · '+esc(stationTypes[s.type]||s.type):' · '+num(s.distance)+' km'}${showExposure?' · '+esc(sector(state)):''}`);
  marker.on('click',()=>chooseStation(s.code));container.addLayer(marker);
 }
 points.addLayer(container);
 $('standardKey').hidden=showExposure;$('exposureKey').hidden=!showExposure;
 const count=pool.filter(hasPosition).length;
 $('visibleCount').textContent=count+(showNational?` / ${D.nationalStations.length} national stations`:' event stations')+' shown';
 $('exposureCount').textContent=count+' spatial pairs shown';
 const w=wind();if(w?.status==='NONCALM'&&Number.isFinite(w.toward)&&Number.isFinite(w.speed)&&w.speed>0&&hasPosition(event)){
  const bearing=w.toward,end=destination(event.lat,event.lon,bearing,18),left=destination(end[0],end[1],bearing+145,4),right=destination(end[0],end[1],bearing-145,4);
  L.polyline([[event.lat,event.lon],end],{color:'#d76724',weight:4,opacity:.85,interactive:false}).addTo(windOverlay);
  L.polyline([left,end,right],{color:'#d76724',weight:4,opacity:.85,interactive:false}).addTo(windOverlay);
 }
}
function renderPmTable(){
 const headers=['Station (code)','Region','Selection','Downwind hours','Pollutant','Prefire min–max','Prefire mean (SD)','Active min–max','Active mean (SD)','Active mean anomaly','Postfire min–max','Postfire mean (SD)','Postfire mean anomaly'];
 const rows=window.PM_TABLE_CELLS?.[event.id]||[];
 $('pmReadableTable').innerHTML='<thead><tr>'+headers.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map((r,i)=>'<tr>'+r.map((x,j)=>j<4?(i%2?'':'<td rowspan="2">'+esc(x)+'</td>'):'<td>'+esc(x)+'</td>').join('')+'</tr>').join('')+'</tbody>';
}
function renderGraph(){const src=event.graphs.anomaly;$('graphImage').src=src;$('graphImage').alt=`${event.name}: hourly PM anomalies from the supplied analysis`;$('downloadPdf').href='assets/All_Wildfires_PM_Anomalies.pdf';$('graphError').hidden=true;$('eventTablePdf').href=event.tablePdf;renderPmTable();}
function render(){renderHeader();renderStation();renderWind();renderMap();renderTable();renderGraph();}
$('eventCount').textContent=D.events.length;
$('eventSelect').innerHTML=D.events.map(e=>`<option value="${e.id}">Event ${e.number} · ${esc(e.name)} · ${e.start.slice(0,4)}</option>`).join('');
$('eventList').innerHTML=D.events.map(e=>`<button class="event-button" data-event="${e.id}"><span class="event-number">${String(e.number).padStart(2,'0')}</span><span><strong>${esc(e.name)}</strong><small>${e.start.slice(0,10)} · ${num(e.area,0)} ha</small></span></button>`).join('');
$('eventSelect').addEventListener('change',e=>showEvent(e.target.value));
document.addEventListener('click',e=>{const fire=e.target.closest('[data-event]');if(fire)showEvent(fire.dataset.event);const s=e.target.closest('[data-station]');if(s)chooseStation(s.dataset.station);});
$('stationLayer').addEventListener('change',()=>{renderStation();renderMap();renderTable();});
$('distanceFilter').addEventListener('change',()=>{renderMap();renderTable();});
$('stationSearch').addEventListener('input',()=>{renderMap();renderTable();const hits=layer()==='national'?national():stations();if(query()&&hits.length===1&&hasPosition(hits[0]))map.setView([hits[0].lat,hits[0].lon],12,{animate:false});});
$('toggleCandidates').onclick=()=>{tableExpanded=!tableExpanded;renderTable();};
$('allFires').onclick=fitAll;$('fitEvent').onclick=fitEvent;$('zoomIn').onclick=()=>map.zoomIn();$('zoomOut').onclick=()=>map.zoomOut();
map.on('mousemove',e=>{$('coordinates').textContent=`${e.latlng.lat.toFixed(4)}° N, ${e.latlng.lng.toFixed(4)}° E`;});
function setHour(h){hour=Math.max(0,Math.min(event.wind.length-1,h));renderWind();renderStation();renderTable();renderMap();}
$('windTime').addEventListener('input',e=>setHour(Number(e.target.value)));$('previousHour').onclick=()=>setHour(hour-1);$('nextHour').onclick=()=>setHour(hour+1);
$('graphImage').onerror=()=>{$('graphError').hidden=false;};
$('sourceNotes').innerHTML=D.notes.map(n=>`<p>${esc(n)}</p>`).join('');$('sourceFiles').innerHTML=D.sources.map(s=>`<li>${esc(s.path)}</li>`).join('');
$('sourcesButton').onclick=$('footerSources').onclick=()=>$('sourceDialog').showModal();$('closeSources').onclick=()=>$('sourceDialog').close();
render();fitAll();
})();
