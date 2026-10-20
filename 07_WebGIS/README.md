# South Korea Wildfire–Air Quality WebGIS — updated results

Replace your existing 07_WebGIS folder with this complete folder. Keep a copy of the previous folder before replacing it. No raw data or analysis scripts need to be rerun.

## Open from VS Code

Open a terminal in 07_WebGIS:

    py -m pip install -r requirements.txt
    py run_webgis.py

The existing START_WEBGIS.bat / run_windows.bat launchers are retained.

For the browser-only viewer with no third-party Python packages:

    py serve.py

Or open index.html directly. Online access is needed for basemap tiles. The research results, graphs, tables and map libraries are bundled locally.

## Current contents

- 10 chronologically numbered wildfire events.
- 688 national inventory stations, retained from the supplied platform.
- 241 event–station spatial pairs within 50 km (192 distinct station codes).
- 202 pairs pass paired PM completeness >=75% over the screening window.
- 184 pairs in the saved PM analysis pool: completeness pass AND (within 25 km OR >=5 downwind hours).
- 46 final selected pairs: two nearest qualifying pairs, then up to three other pairs ranked by downwind hours. Events 1 and 2 have three final selected stations each; events 3–10 have five each.
- 1,657 event-level hourly wind records and 45,888 station-hour wind-alignment records.

The wind-alignment layer includes all spatial pairs, including pairs without PM observations. Use separate layers for completeness pass, the PM analysis pool and the final selected stations. Search supports station name or code. The distance filter changes display only. All national stations remain a separate layer.

Detailed PM baselines and anomalies supplied in this package cover the 46 final selected pairs only. Other PM-selected pairs are shown with their selection and availability status, without stale PM values. This does not mean their PM analysis was not performed.

## Graphs, tables and downloads

The latest saved anomaly PNGs and combined PDF replace the previous figures. Tables have merged station details spanning the two pollutant rows. Each station has separate PM2.5 and PM10 statistics; these are not extra stations.

Downloads include combined and individual-event PDF tables, Excel tables, per-event station and PM CSVs, the full final station selection audit, all-pair wind summaries and hourly wind classifications. No HTML table files are generated. Graphs and table PDFs were copied unchanged; their statistics were not recomputed. Preview PNGs were rendered from the supplied table PDFs for display.

## Future refresh

The included build_data.py reads saved outputs in the adjacent project folders:

- 04_KMA_Downwind_Analysis/Results_All_Spatial_Pairs
- 06_PM_Timeseries_Graphs/Results_Best5_Graphs_and_Summary_Tables

Run `py build_data.py` only when you intentionally want to refresh the bundled data and copied outputs. It does not run scientific analysis. inventory_seed.json retains the national inventory and event names/areas from this uploaded platform; update that file deliberately if the source inventory or event set changes. Existing original source provenance is recorded in source_manifest.json. New source files have SHA-256 fingerprints.

Table preview PNGs are packaged in this release. After a future rebuild, regenerate previews from changed PDFs or remove the outdated preview PNGs; PDF downloads remain authoritative.

## Interpretation

All times are KST. Fire markers are officially reported ignition points, not burned-area polygons. Source datum and accuracy remain unspecified. Original project event time windows are retained. Absence of PM observations does not establish historical non-operation. Proximity, hourly wind alignment and PM anomalies do not independently prove smoke exposure or wildfire causation. See the in-app data notes for baseline and wind definitions.

## Verification

Python and JavaScript syntax passed. Data/asset checks and event/layer control-flow checks passed for both viewers. Interactive browser rendering and the actual Streamlit runtime were not available in the build environment; check the viewer locally after opening it. No PM or wind analysis was rerun.

## Readability update

The map spans the full content width (850 px in Streamlit; responsive 650–1050 px in the static viewer). Station and PM tables use light-blue headers, white content cells and dark text. PM tables now render saved Excel cell text with horizontal scrolling instead of a reduced image. Station details remain merged across the two pollutant rows. PDF/Excel download statistics and original documents are unchanged. No separate HTML table files are generated.

## Map and details layout

Event details are restored beside the map in a narrower right panel. Streamlit uses a 4:1 column ratio. The browser-only viewer uses a 220–260 px details panel, stacking below the map on small screens. The taller map and high-contrast text/table styling are retained.

The map-filtered station table now appears below the map and event-details row at full width, rather than inside the narrow details column.

## Startup map view

A new Streamlit session starts with a nationwide map extent showing South Korea, all fire markers and the enabled national station inventory. Event 1 details remain selected. Selecting another event in the dropdown or clicking another wildfire marker switches to that event's closer view. The browser-only viewer already opens at national extent.

## Fire marker clicks

Double-click zoom is disabled to prevent repeated marker clicks from zooming the map. Zoom buttons and mouse-wheel zoom remain available. In Streamlit, choosing a fire opens its details popup immediately after event selection; the map key remains stable when changing filters or the wind hour.

The startup extent now uses a national view at zoom 7 instead of fitting a wider bounding box. The map display radius ranges from 5 to 100 km (default 50 km). Values above 50 km enlarge the display circle only; the saved 241 event–station pairs remain within the original 50 km analysis radius.

The map layer previously labeled PM completeness pass is now labeled Eligible stations. Eligibility remains distance <=50 km and paired PM completeness >=75%; the 25 km/downwind criterion is applied separately for the PM analysis pool.

## Hourly alignment of final selected stations

Choose Final selected stations — hourly wind alignment to show only the final selected stations, colored using their saved classification at the selected KMA/AWS hour. Event 1 shows three station markers when the display radius includes them and no search excludes them. The national inventory is hidden for this layer. Orange = downwind, blue = upwind, purple = crosswind, gray = calm or missing wind. The original all-candidate hourly alignment layer is retained. Scientific selection and wind classifications are unchanged.

Interface update: download controls offer only PM anomaly graph PDF and event/all-event PM summary table PDFs. The Spatial candidate layer replaces All spatial pairs. Supporting source files remain bundled for the app.
