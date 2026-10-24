"""Streamlit research explorer built exclusively from this project's data.js and figures.

Run from VS Code with: python run_webgis.py
"""
from __future__ import annotations

import csv
import html
import io
import json
import math
import re
from pathlib import Path

import folium
import streamlit as st
from folium.plugins import MarkerCluster, MeasureControl
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="South Korea Wildfire–Air Quality Explorer", page_icon="🔥", layout="wide")


st.markdown("""<style>
.block-container{max-width:100%;padding:1.5rem 2rem 3rem}
html,body,[data-testid="stAppViewContainer"],p,label{color:#111827}
[data-testid="stMarkdownContainer"] p,[data-testid="stCaptionContainer"],label{font-size:17px!important;color:#1f2937!important}
h1{font-size:32px!important}h2{font-size:26px!important}h3{font-size:22px!important}
.stSelectbox label,.stSlider label,.stTextInput label{font-size:17px!important;font-weight:600}
.readable-table-wrap{overflow-x:auto;margin:16px 0;background:white}
table.readable-table{border-collapse:collapse;width:100%;min-width:1000px;font-size:17px;color:#000;background:white}
table.readable-table th{background:#dceeff;color:#000;font-weight:700;border:1px solid #afc5da;padding:14px 12px;text-align:left}
table.readable-table td{background:white;color:#000;border:1px solid #cdd6df;padding:13px 12px;vertical-align:middle}
table.pm-table{min-width:1780px;font-size:16px}
</style>""",unsafe_allow_html=True)

def clear_table(rows, headers=None, merge_station=False):
    if not rows:
        st.info('No matching rows.');return
    if isinstance(rows[0],dict):
        headers=list(rows[0]);values=[[r.get(k,'') for k in headers] for r in rows]
    else:
        values=rows
    body=[]
    for i,row in enumerate(values):
        cells=[]
        for j,value in enumerate(row):
            if merge_station and j<4 and i%2:continue
            span=' rowspan="2"' if merge_station and j<4 else ''
            if value is None:value='—'
            elif isinstance(value,float):value=fmt(value,2)
            cells.append(f'<td{span}>{safe(value)}</td>')
        body.append('<tr>'+''.join(cells)+'</tr>')
    klass='readable-table pm-table' if merge_station else 'readable-table'
    markup='<div class="readable-table-wrap"><table class="'+klass+'"><thead><tr>'+''.join('<th>'+safe(k)+'</th>' for k in headers)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'
    st.markdown(markup,unsafe_allow_html=True)


@st.cache_data
def load_archive() -> dict:
    source = (ROOT / "data.js").read_text(encoding="utf-8")
    prefix = "window.WILDFIRE_DATA = "
    if not source.startswith(prefix):
        raise ValueError("data.js is missing or is not a WebGIS archive")
    archive = json.loads(source[len(prefix):].strip().removesuffix(";"))
    english_by_code = {station["code"]: station["nameEn"]
                       for event in archive["events"] for station in event["stations"]
                       if station.get("nameEn") and station["nameEn"] != station["name"]}
    for station in archive["nationalStations"]:
        station["nameEn"] = english_by_code.get(station["code"], station.get("nameEn") or station["name"])
    return archive


def station_name(station: dict) -> str:
    """Use archived English figure names, preserving the source Korean name."""
    return station.get("nameEn") or station["name"]


def map_station_name(station: dict) -> str:
    english = station_name(station)
    korean = station["name"]
    return f"{english} / {korean}" if english != korean else korean


def safe(value: object) -> str:
    return html.escape(str(value if value is not None else "—"))


def fmt(value: object, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
        return f"{n:,.{digits}f}" if math.isfinite(n) else "—"
    except (TypeError, ValueError):
        return "—"


def coords(item: dict) -> bool:
    return isinstance(item.get("lat"), (float, int)) and isinstance(item.get("lon"), (float, int))


def rows_csv(rows: list[dict], fields: list[tuple[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([label for _, label in fields])
    for row in rows:
        writer.writerow([station_name(row) if key == "name" and label == "Station" else assessment_category(row) if key == "assessmentCategory" else selection_stage(row) if key == "selectionStage" else row.get(key, "") for key, label in fields])
    return out.getvalue().encode("utf-8-sig")


def destination(lat: float, lon: float, bearing: float, distance_km: float) -> tuple[float, float]:
    radius = 6371.0088
    a, b, theta, d = map(math.radians, (lat, lon, bearing, distance_km / radius * 180 / math.pi))
    end_lat = math.asin(math.sin(a) * math.cos(d) + math.cos(a) * math.sin(d) * math.cos(theta))
    end_lon = b + math.atan2(math.sin(theta) * math.sin(d) * math.cos(a), math.cos(d) - math.sin(a) * math.sin(end_lat))
    return math.degrees(end_lat), math.degrees(end_lon)


def assessment_category(station: dict) -> str:
    labels = {
        "DOWNWIND_AND_VERY_CLOSE": "Very close (≤25 km) and downwind-qualified (≥5 hours)",
        "VERY_CLOSE": "Very close (≤25 km)",
        "DOWNWIND": "Downwind-qualified (≥5 hours)",
        "NEITHER": "Neither proximity nor downwind criterion met",
    }
    category = station.get("category") or ""
    return labels.get(category, category or "Not recorded")


def selection_stage(station: dict) -> str:
    labels = {
        "NEAREST": "Two-nearest stage",
        "DOWNWIND_PRIORITY": "Additional station ranked by downwind hours",
    }
    role = station.get("selectionRole") or ""
    return labels.get(role, role or "Not in final selected stations")


STATION_COLORS = {"도시대기": "#2878b5", "교외대기": "#2ca25f", "도로변대기": "#7b3294",
                  "국가배경": "#e6ab02", "국가배경농도": "#e6ab02", "항만": "#008c95", "산단대기": "#636363"}
EXPOSURE_COLORS = {"DOWNWIND": "#d76724", "UPWIND": "#2878b5", "CROSSWIND": "#7b539e",
                   "CALM": "#8494a2", "MISSING": "#8494a2"}
STATION_FIELDS = [("code", "Station code"), ("name", "Station"), ("name", "Korean station name"), ("distance", "Distance (km)"),
                  ("eligible", "Eligible stations"), ("pmSelected", "PM analysis pool"), ("analyzed", "Final selected stations"),
                  ("availability", "PM availability"), ("assessmentCategory", "Assessment category"), ("selectionStage", "Selection stage"), ("downwindHours", "Downwind hours"),
                  ("completeness", "Paired PM completeness (%)"), ("downwindPercent", "Downwind / noncalm (%)"),
                  ("baseline25", "Prefire PM2.5 (µg/m³)"), ("baseline10", "Prefire PM10 (µg/m³)"),
                  ("anomaly25", "Active PM2.5 anomaly (µg/m³)"), ("anomaly10", "Active PM10 anomaly (µg/m³)")]


def build_map(archive: dict, event: dict, stations: list[dict], national: list[dict],
              radius: int, view: str, wind: dict | None, overview: bool = False) -> folium.Map:
    m = folium.Map(location=[36.3, 127.9] if overview else ([event['lat'], event['lon']] if coords(event) else [36.3, 127.9]),
                   zoom_start=7 if overview else (10 if coords(event) else 7), tiles=None, control_scale=True, double_click_zoom=False)
    m.get_root().header.add_child(folium.Element('''<style>
    .leaflet-tooltip.wildfire-number-label {font-size:11px;font-weight:700;line-height:14px;
        padding:1px 4px;border:1px solid #b95331;border-radius:3px;color:#872f19;
        background:#fff;box-shadow:none;min-width:14px;text-align:center;}
    .wildfire-number-label:before {display:none;}
    </style>'''))
    folium.TileLayer(tiles="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                     attr="© OpenStreetMap contributors", name="OpenStreetMap", max_zoom=19,
                     show=True).add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
                     attr="Tiles © Esri; sources: Esri, HERE, Garmin, USGS, Intermap, NRCan, Esri Japan, METI, © OpenStreetMap contributors, GIS User Community",
                     name="Esri World Street Map", max_zoom=18, show=False).add_to(m)
    fire_layer = folium.FeatureGroup(name="10 officially reported ignition points", show=True)
    for fire in archive["events"]:
        if not coords(fire):
            continue
        selected = fire["id"] == event["id"]
        description = (f"<b>Event {fire['number']}: {safe(fire['name'])}</b><br>{safe(fire['nameKo'])}<br>"
                       f"Start: {safe(fire['start'])} KST<br>End: {safe(fire['end'])} KST<br>"
                       f"Reported area: {fmt(fire['area'], 2)} ha<br>"
                       f"Coordinates: {fmt(fire['lat'], 5)}, {fmt(fire['lon'], 5)}<br>"
                       "Officially reported ignition point; not a burn perimeter.")
        # Opposite permanent labels keep the close Event 2/5 pair identifiable.
        label_direction = "left" if fire["number"] == 2 else "right"
        folium.Marker([fire["lat"], fire["lon"]],
                      tooltip=folium.Tooltip(str(fire['number']), permanent=True, sticky=False,
                                            direction=label_direction, class_name="wildfire-number-label"),
                      title=f"Event {fire['number']} · {fire['name']}",
                      popup=folium.Popup(description, max_width=350, show=selected and not overview),
                      z_index_offset=2000 if selected else 1000,
                      icon=folium.Icon(color="red" if selected else "darkred", icon="fire", prefix="fa")).add_to(fire_layer)
    fire_layer.add_to(m)
    if coords(event):
        folium.Circle([event["lat"], event["lon"]], radius=radius * 1000,
                      color="#d73027", weight=2, fill=True, fill_opacity=.035,
                      tooltip=f"Map distance: {radius} km (display filter only)").add_to(m)
    if national:
        group = folium.FeatureGroup(name="National AirKorea stations", show=True)
        cluster = MarkerCluster(options={"disableClusteringAtZoom": 12}).add_to(group)
        for station in national:
            if not coords(station):
                continue
            popup = (f"<b>{safe(map_station_name(station))} ({safe(station['code'])})</b><br>"
                     f"English label source: {safe(station.get('nameEnSource', 'Existing project figure name'))}<br>"
                     f"Type: {safe(station['type'])}<br>Province: {safe(station['province'])}<br>"
                     f"Address: {safe(station['address'])}<br>"
                     "National inventory; detailed PM results are bundled only for final selected stations.")
            folium.CircleMarker([station["lat"], station["lon"]], radius=4,
                                color=STATION_COLORS.get(station["type"], "#7f8c8d"),
                                fill=True, fill_opacity=.8, tooltip=f"{map_station_name(station)} ({station['code']})",
                                popup=folium.Popup(popup, max_width=350)).add_to(cluster)
        group.add_to(m)
    group = folium.FeatureGroup(name=f"Event {event['number']} {view.lower()} stations", show=True)
    for station in stations:
        if not coords(station):
            continue
        state = station["exposure"].get(wind["time"], "MISSING") if wind else "MISSING"
        color = (EXPOSURE_COLORS.get(state, EXPOSURE_COLORS["MISSING"]) if view in ["Hourly wind alignment", "Final selected stations — hourly wind alignment"]
                 else "#0b7a53" if station["analyzed"] else "#1678a8" if station["eligible"] else "#737c78")
        popup = (f"<b>{safe(map_station_name(station))} ({safe(station['code'])})</b><br>"
                 f"English label source: {safe(station.get('nameEnSource', 'Existing project figure name'))}<br>"
                 f"Distance: {fmt(station['distance'], 2)} km<br>"
                 f"Saved selection: {'Final selected' if station['analyzed'] else 'PM analysis pool' if station['pmSelected'] else 'Eligible station' if station['eligible'] else 'PM completeness not met'}<br>"
                 f"PM availability: {safe(station['availability'])}<br>"
                 f"Paired PM completeness: {fmt(station['completeness'])}%<br>"
                 f"Downwind hours: {fmt(station['downwindHours'],0)}<br>"
                 f"Assessment category: {safe(assessment_category(station))}<br>"
                 f"Selection stage: {safe(selection_stage(station))}<br>"
                 f"Sector at selected hour: {safe(state)}<br>"
                 f"Active PM2.5 anomaly: {fmt(station['anomaly25'])} µg/m³<br>"
                 f"Active PM10 anomaly: {fmt(station['anomaly10'])} µg/m³")
        folium.CircleMarker([station["lat"], station["lon"]], radius=9 if station["analyzed"] else 6,
                            color="white", weight=2, fill=True, fill_color=color, fill_opacity=.95,
                            tooltip=f"{map_station_name(station)} ({station['code']})",
                            popup=folium.Popup(popup, max_width=350)).add_to(group)
    group.add_to(m)
    if wind and wind["status"] == "NONCALM" and wind["toward"] is not None and coords(event):
        start = (event["lat"], event["lon"])
        end = destination(*start, wind["toward"], 18)
        folium.PolyLine([start, end], color="#d76724", weight=4,
                        tooltip="Event-level wind direction; arrow length is illustrative").add_to(m)
        left = destination(*end, (wind["toward"] + 145) % 360, 4)
        right = destination(*end, (wind["toward"] - 145) % 360, 4)
        folium.PolyLine([left, end, right], color="#d76724", weight=4).add_to(m)
    MeasureControl(position="bottomleft", primary_length_unit="kilometers").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


archive = load_archive()
events = archive["events"]
event_by_number = {e["number"]: e for e in events}
st.title("South Korea Wildfire–Air Quality Explorer")
st.caption("Web GIS-Based Integrated Wildfire–Air Quality Monitoring Network Exploration Platform for South Korea")

if 'overview_map' not in st.session_state:
    st.session_state.overview_map = True

def focus_selected_event():
    st.session_state.overview_map = False

if "pending_event" in st.session_state:
    st.session_state.selected_event = st.session_state.pop("pending_event")
    st.session_state.overview_map = False

with st.sidebar:
    st.header("Select an event")
    selected = st.selectbox("Wildfire event", list(event_by_number),
                            format_func=lambda n: f"Event {n:02d} — {event_by_number[n]['name']}", key="selected_event", on_change=focus_selected_event)
    event = event_by_number[selected]
    radius = st.slider("Map display radius (km)", 5, 100, 50, 5,
                       help="Changes the display circle and filters existing event pairs. Assessed event pairs are available only within 50 km; selecting 50–100 km does not recalculate the analysis.")
    if radius > 50:
        st.caption('The display circle extends beyond 50 km. Assessed event–station pairs remain limited to the original 50 km analysis radius; the national inventory is a separate layer.')
    view = st.selectbox("Event station layer", ["Spatial candidate", "Eligible stations", "PM analysis pool", "Final selected stations", "Hourly wind alignment", "Final selected stations — hourly wind alignment"])
    if view == 'Final selected stations — hourly wind alignment':
        show_national = False
        st.caption('Only final selected stations are shown in this layer. Colors follow the selected KMA/AWS hour; the national inventory is hidden.')
    else:
        show_national = st.checkbox(f"Show all {len(archive['nationalStations'])} AirKorea stations", value=True)
    search = st.text_input("Search station name or code", placeholder="English or Korean name, or station code").strip().casefold()
    wind_records = event["wind"]
    hour = st.slider("KMA/AWS hour", 0, max(0, len(wind_records) - 1), 0, disabled=not wind_records)
    wind = wind_records[hour] if wind_records else None
    if wind:
        st.caption(f"{wind['time']} KST · {fmt(wind['speed'], 2)} m/s · "
                   + (f"{fmt(wind['toward'], 0)}° toward" if wind['toward'] is not None else wind['status']))
    st.caption("Hourly exposure uses archived KMA/AWS sector classifications; it is not a smoke model.")


def matches(station: dict) -> bool:
    return not search or search in " ".join(str(station.get(k, "")) for k in
                                       ("name", "nameEn", "code", "province", "city", "address")).casefold()


visible = [s for s in event["stations"] if (s["distance"] is None or s["distance"] <= radius)
           and (view in ["Spatial candidate", "Hourly wind alignment"] or (s["eligible"] if view == "Eligible stations" else s["pmSelected"] if view == "PM analysis pool" else s["analyzed"])) and matches(s)]
national = [s for s in archive["nationalStations"] if matches(s)] if show_national else []
left, right = st.columns([4, 1], gap="medium")
with left:
    result = st_folium(build_map(archive, event, visible, national, radius, view, wind, st.session_state.overview_map),
                       height=850, use_container_width=True,
                       returned_objects=["last_object_clicked_tooltip"],
                       key=f"research-map-{selected}-{st.session_state.overview_map}")
    clicked = (result or {}).get("last_object_clicked_tooltip") or ""
    if clicked.startswith("Wildfire Event ") or clicked.isdigit():
        try:
            new_event = int(clicked.removeprefix("Wildfire Event "))
            if new_event in event_by_number and (new_event != selected or st.session_state.overview_map):
                st.session_state.pending_event = new_event
                st.rerun()
        except ValueError:
            pass
    elif clicked and clicked != st.session_state.get('last_map_station_click'):
        station_match = re.search(r'\((\d{6})\)$', clicked)
        if station_match and any(s['code']==station_match[1] for s in event['stations']):
            st.session_state.last_map_station_click = clicked
            st.session_state.station_selector = station_match[1]
            st.rerun()
    st.caption("Map colors: event layer green = final selected stations; blue = eligible stations; gray = completeness not met. "
               "Hourly exposure layer orange = downwind; blue = upwind; purple = crosswind; gray = calm/missing. "
               "National station colors indicate station type. Wind sectors do not establish wildfire causation.")
with right:
    st.subheader(f"Event {selected:02d} details")
    st.write(f"**Location:** {event['name']} ({event['nameKo']})")
    st.write(f"**Start:** {event['start']} KST")
    st.write(f"**End:** {event['end']} KST")
    st.write(f"**Reported burned area:** {fmt(event['area'], 2)} ha")
    st.write(f"**Coordinates:** {fmt(event['lat'], 5)}, {fmt(event['lon'], 5)}")
    st.info(f"**Location quality:** {event['precision']} · {event['verification']}. "
            "The marker is an officially reported ignition point. Source CRS/datum and accuracy are unspecified; the existing mapping convention is retained.")
    st.metric("Event stations displayed", len(visible))
    st.caption(f"{len(event['stations'])} assessed candidates · "
               f"{sum(s['eligible'] for s in event['stations'])} eligible stations · "
               f"{sum(s['pmSelected'] for s in event['stations'])} PM analysis pool · "
               f"{sum(s['analyzed'] for s in event['stations'])} final selected stations · "
               f"wind coverage {fmt(event['windCoverage'])}% ({event['windQuality']}).")
    if wind:
        st.write(f"**Selected wind hour:** {wind['time']} KST · {wind['status']}")
        st.caption(f"Reporting KMA/AWS sources: {fmt(wind['reporting'], 0)}. The arrow shows an event-level "
                   "transport bearing; its length does not indicate plume extent.")

st.subheader("Stations shown on the map")
st.caption("The current event layer, distance filter and station search determine these rows.")
clear_table([{ "Code": s["code"], "Station": station_name(s), "Distance (km)": s["distance"],
                "PM complete (%)": s["completeness"], "Final selected stations": s["analyzed"], "PM availability": s["availability"], "PM analysis pool": s["pmSelected"], "Downwind hours": s["downwindHours"],
                "Assessment category": assessment_category(s), "Selection stage": selection_stage(s),
                "Selected-hour sector": s["exposure"].get(wind["time"], "MISSING") if wind else "MISSING"}
              for s in visible])

st.divider()
st.subheader(f"Event {selected:02d} final selected stations and PM results")
analyzed = [s for s in event["stations"] if s["analyzed"]]
clear_table([{"Station": station_name(s), "Code": s["code"], "Distance (km)": s["distance"],
               "PM complete (%)": s["completeness"], "Downwind / noncalm (%)": s["downwindPercent"],
               "Assessment category": assessment_category(s), "Selection stage": selection_stage(s),
               "Prefire PM2.5": s["baseline25"], "Prefire PM10": s["baseline10"],
               "Active PM2.5 anomaly": s["anomaly25"], "Active PM10 anomaly": s["anomaly10"]}
              for s in analyzed])
st.caption("Prefire baselines and active-fire mean anomalies are in µg/m³. Missing values remain missing. "
           "These are saved analysis results; map filters do not recompute them.")

st.subheader("Selected station details")
options = {s["code"]: s for s in event["stations"]}
if options:
    codes = list(options)
    if st.session_state.get("station_selector") not in options:
        st.session_state.station_selector = codes[0]
    chosen = st.selectbox("Event station", codes, key="station_selector",
                          format_func=lambda code: f"{station_name(options[code])} ({code})")
    s = options[chosen]
    st.caption(f"Original Korean station name: {s['name']} · {s.get('nameEnSource', 'Existing project figure name')}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distance", fmt(s["distance"], 2) + " km")
    c2.metric("PM completeness", fmt(s["completeness"]) + "%")
    c3.metric("Downwind / noncalm", fmt(s["downwindPercent"]) + "%")
    c4.metric("Selected-hour sector", s["exposure"].get(wind["time"], "MISSING") if wind else "MISSING")
    st.write(f"**PM availability:** {s['availability']} · **PM analysis pool:** {'Yes' if s['pmSelected'] else 'No'}")
    st.write(f"**Downwind hours:** {fmt(s['downwindHours'],0)} · **Assessment category:** {assessment_category(s)}")
    st.write(f"**Selection stage:** {selection_stage(s)}")
    st.caption("The selection stage records how the saved final subset is ranked. "
               "Additional stations are ranked by downwind hours, which may be zero; "
               "this stage does not itself establish downwind qualification.")
    st.write(f"**Baseline quality:** {s['baselineQuality']}")
    if not s['analyzed']:
        st.caption('Detailed PM baseline and anomaly values are bundled only for the final selected stations.')

st.subheader("Hourly PM anomalies")
anomaly_tab, download_tab = st.tabs(["PM anomalies", "Downloads"])
with anomaly_tab:
    try:
        st.image(str(ROOT / event["graphs"]["anomaly"]), caption=f"Event {selected:02d}: hourly PM anomaly figure")
        st.caption("Saved figure generated from the project's hourly analysis. The app does not regenerate the plot.")
    except (OSError, ValueError) as error:
        st.error("The saved anomaly image could not be opened. Replace the event's PNG from the updated platform package.")
        st.caption(f"Image error: {error}. PM summary tables and downloads remain available below.")
with download_tab:
    filename = "All_Wildfires_PM_Anomalies.pdf"
    st.download_button("Download all-event PM anomalies PDF", (ROOT / "assets" / filename).read_bytes(),
                       filename, "application/pdf", key="download-anomaly")

st.subheader("PM summary tables")
st.caption("Station-specific PM statistics and mean anomalies for the prefire, active-fire, and postfire periods.")
table_root = ROOT/'assets'/'tables'
event_pdf = table_root/f'Event_{selected:02d}_PM_Summary_Table.pdf'
table_cells=json.loads((table_root/'table_cells.json').read_text(encoding='utf-8'))
headers=['Station (code)','Region','Selection','Downwind hours','Pollutant','Prefire min–max','Prefire mean (SD)','Active min–max','Active mean (SD)','Active mean anomaly','Postfire min–max','Postfire mean (SD)','Postfire mean anomaly']
clear_table(table_cells[event['id']],headers,merge_station=True)
st.caption('Scroll horizontally to see all columns. Saved values are displayed as text, with merged station details; PDF downloads remain available below.')
st.download_button('Download this event PM summary (PDF)', event_pdf.read_bytes(), event_pdf.name, 'application/pdf')
filename = 'All_Events_PM_Summary_Tables.pdf'
st.download_button('Download all-event PM tables (PDF)', (table_root/filename).read_bytes(), filename, 'application/pdf')

with st.expander("Methods, source files and interpretation limits"):
    for note in archive["notes"]:
        st.markdown("- " + note)
    st.markdown("Map distance and layer controls change the display only. They do not recalculate eligibility, "
                "saved downwind classifications, PM baselines, or anomaly figures. Wind sectors and PM anomalies "
                "do not independently prove wildfire smoke causation.")
