# A2GeoLens

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![QGIS 3.x](https://img.shields.io/badge/QGIS-3.x-589632?logo=qgis&logoColor=white)
![GeoJSON](https://img.shields.io/badge/GeoJSON-web%20ready-23836B)

**Walkability & amenity access analysis for Ann Arbor census tracts using QGIS-ready geospatial assets, OpenStreetMap data, Census geography, and an interactive web map.**

Live map: <https://vittorio-centore.github.io/A2GeoLens/>

![A2GeoLens QGIS-style map export](docs/screenshots/hero_map.png)

## Project Scope

A2GeoLens is an end-to-end geospatial asset workflow. It downloads open map features for Ann Arbor, prepares Census tract geography, computes tract-level accessibility metrics, styles the outputs for QGIS, and publishes the results as a static interactive map.

The project is designed to demonstrate the kind of practical QGIS and geospatial production work needed to build and refine digital map assets: clean source layers, reproducible transformations, CRS-aware analysis, styled vector outputs, screenshot exports, and web-ready GeoJSON deliverables.

## Relevance To QGIS Digital Asset Work

This repository includes a starter QGIS project and reusable QGIS style files:

- `qgis/a2geolens.qgz` and `qgis/a2geolens.qgs` for project handoff
- `qgis/styles/tracts_walkability.qml` for graduated tract symbology
- `qgis/styles/parks.qml`, `bike_lanes.qml`, `transit_stops.qml`, `grocery.qml`, and `schools.qml` for supporting layers
- `qgis/README.md` with a desktop QGIS finishing checklist

Skills demonstrated for a QGIS-focused mapping role:

- QGIS project organization and layer styling
- QML style asset creation for repeatable symbology
- Graduated choropleth mapping by analytic score
- Vector layer preparation for polygons, lines, and points
- CRS selection and reprojection for distance-safe analysis
- Spatial joins, clipping, buffering, and nearest-feature measurement
- OpenStreetMap feature extraction and cleanup
- Census tract filtering and GeoJSON publication
- Static map export preparation for documentation and review
- Web map packaging for digital asset QA and sharing

## Outputs

| Output | Location |
| --- | --- |
| Interactive map | `docs/index.html` |
| GitHub Pages map | <https://vittorio-centore.github.io/A2GeoLens/> |
| Scored tract GeoJSON | `docs/data/tracts_scored.geojson` |
| QGIS project | `qgis/a2geolens.qgz` |
| QGIS style assets | `qgis/styles/*.qml` |
| Map screenshots | `docs/screenshots/*.png` |
| OSM fetch script | `scripts/fetch_osm.py` |
| Access scoring script | `scripts/compute_access.py` |

The web map can be served over HTTP or opened directly from `docs/index.html`; JavaScript data bundles in `docs/data/*.js` make direct file preview work without browser GeoJSON fetch restrictions.

## Methodology

OpenStreetMap features are downloaded with OSMnx for Ann Arbor, Michigan. The pipeline extracts parks, bike infrastructure, transit stops, schools, and grocery stores, then saves each layer as GeoJSON for QGIS and web use.

Census tract geometry is fetched with pygris from 2020 Census TIGER/Line cartographic boundary data for Washtenaw County. Tracts are retained when their centroid falls inside Ann Arbor or at least 25% of the tract overlaps the city boundary.

Storage and web outputs use EPSG:4326 for broad compatibility. Distance and length analysis uses EPSG:3078, a Michigan meter-based projected CRS, so buffers, nearest-feature distances, and bike-lane lengths are measured in meters.

The final score combines four normalized components: parks intersecting an 800-meter tract buffer, transit stops within each tract, clipped bike-lane length in meters, and distance from tract centroid to the nearest grocery store. Grocery distance is inverted so closer access scores higher. The final `walkability_score` is an unweighted 0-100 score.

## Tech Stack

QGIS 3.x, Python, GeoPandas, OSMnx, Shapely, pygris, Leaflet, GeoJSON, GitHub Pages.

## Setup

```bash
git clone https://github.com/vittorio-centore/A2GeoLens.git
cd A2GeoLens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If the geospatial Python stack fails to install with pip, use conda or mamba for GeoPandas, PyProj, Shapely, and Pyogrio, then install the remaining requirements.

Fetch OSM data:

```bash
python scripts/fetch_osm.py
```

Compute tract scores:

```bash
python scripts/compute_access.py
```

Regenerate screenshot assets and local JS data bundles:

```bash
python scripts/render_screenshots.py
```

Preview the web map:

```bash
cd docs
python -m http.server 8000
```

Then open <http://localhost:8000>.

## QGIS Workflow

Open `qgis/a2geolens.qgz` in QGIS 3.x. If QGIS asks to repair layer paths, point it at the matching GeoJSON files in `data/raw/` and `data/processed/`, then re-save the project.

Recommended desktop finishing steps:

1. Set project CRS to EPSG:4326.
2. Add an OpenStreetMap XYZ basemap if desired.
3. Load the scored tract layer and supporting OSM layers.
4. Apply the matching `.qml` styles from `qgis/styles/`.
5. Save the project as `qgis/a2geolens.qgz`.
6. Export final review images to `docs/screenshots/`.

## Screenshots

![Access score choropleth](docs/screenshots/access_score.png)

![Interactive map preview](docs/screenshots/felt_preview.png)

## Limitations

OSM completeness varies by feature type and neighborhood. The score is intentionally unweighted and tract-level, so it does not capture every block-level condition. The 800-meter park buffer is a simple proximity measure rather than a routed sidewalk-network travel distance.

## Data Sources & Licenses

OpenStreetMap data is available under the Open Database License (ODbL). Census TIGER/Line geography is public domain from the U.S. Census Bureau.
