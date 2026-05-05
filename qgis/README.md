# QGIS Finishing Checklist

QGIS is not installed in this development environment, so the project file and layout export need to be completed in the QGIS desktop app.

1. Open QGIS 3.x and set the project CRS to `EPSG:4326`.
2. Add an OpenStreetMap XYZ basemap.
3. Load these layers:
   - `data/processed/tracts_scored.geojson`
   - `data/raw/parks.geojson`
   - `data/raw/bike_lanes.geojson`
   - `data/raw/transit_stops.geojson`
   - `data/raw/grocery.geojson`
   - `data/raw/schools.geojson`
4. Apply the matching styles from `qgis/styles/`.
5. Save the project as `qgis/a2geolens.qgz`.
6. Create a print layout named `Ann Arbor Walkability`.
7. Add map, title, legend, scale bar, north arrow, and OSM/Census attribution.
8. Export the final layout to `docs/screenshots/hero_map.png` at 300 DPI.
9. Export or crop a score-focused view to `docs/screenshots/access_score.png`.

