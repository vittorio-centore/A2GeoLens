"""Download OpenStreetMap layers for A2GeoLens.

Outputs are stored as EPSG:4326 GeoJSON files under data/raw/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import osmnx as ox
import pandas as pd


PLACE = "Ann Arbor, Michigan, USA"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
WGS84 = "EPSG:4326"


def _empty_feature_collection(path: Path) -> None:
    path.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")


def _json_safe(value):
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, sort_keys=True)
    return value


def _clean_for_geojson(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    for column in gdf.columns:
        if column == gdf.geometry.name:
            continue
        if gdf[column].dtype == "object":
            gdf[column] = gdf[column].map(_json_safe)
    return gdf


def _to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf.set_crs(WGS84, allow_override=True)
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(WGS84)


def _dedupe_by_osm_identity(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf

    gdf = gdf.reset_index()
    identity_columns = [col for col in ("element_type", "osmid") if col in gdf.columns]
    if identity_columns:
        gdf = gdf.drop_duplicates(subset=identity_columns)
    else:
        gdf = gdf.drop_duplicates(subset=gdf.geometry.name)
    return gdf


def _clip_to_boundary(gdf: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty or boundary.empty:
        return gdf
    try:
        return gpd.clip(gdf, boundary[["geometry"]])
    except Exception as exc:
        print(f"  warning: clip failed, saving unclipped layer ({exc})")
        return gdf


def _filter_geometry(gdf: gpd.GeoDataFrame, geometry_types: Iterable[str]) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    return gdf[gdf.geometry.geom_type.isin(set(geometry_types))].copy()


def _write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf = _to_wgs84(gdf)
    if gdf.empty:
        _empty_feature_collection(path)
        return
    gdf = _clean_for_geojson(gdf)
    gdf.to_file(path, driver="GeoJSON")


def _download_features(tags: dict, boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    features = ox.features_from_place(PLACE, tags=tags)
    features = _dedupe_by_osm_identity(features)
    features = _to_wgs84(features)
    return _clip_to_boundary(features, boundary)


def _download_union(tag_queries: list[dict], boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    parts: list[gpd.GeoDataFrame] = []
    for tags in tag_queries:
        part = _download_features(tags, boundary)
        if not part.empty:
            parts.append(part)

    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs=WGS84)

    combined = pd.concat(parts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=WGS84)
    return _dedupe_by_osm_identity(combined)


def _run_layer(name: str, filename: str, tags: list[dict], boundary: gpd.GeoDataFrame) -> None:
    output_path = RAW_DIR / filename
    print(f"Downloading {name}...")
    try:
        gdf = _download_union(tags, boundary)

        if name == "bike lanes":
            gdf = _filter_geometry(gdf, ("LineString", "MultiLineString"))

        _write_geojson(gdf, output_path)
        print(f"  saved {len(gdf):,} features -> {output_path.relative_to(RAW_DIR.parents[1])}")
    except Exception as exc:
        print(f"  failed to download {name}: {exc}")
        _empty_feature_collection(output_path)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading city boundary for {PLACE}...")
    try:
        boundary = ox.geocode_to_gdf(PLACE)
        boundary = _to_wgs84(boundary)
        _write_geojson(boundary, RAW_DIR / "ann_arbor_boundary.geojson")
        print(f"  saved {len(boundary):,} boundary feature -> data/raw/ann_arbor_boundary.geojson")
    except Exception as exc:
        print(f"  failed to download city boundary: {exc}")
        boundary = gpd.GeoDataFrame(geometry=[], crs=WGS84)
        _empty_feature_collection(RAW_DIR / "ann_arbor_boundary.geojson")

    layers = [
        ("parks", "parks.geojson", [{"leisure": "park"}]),
        ("bike lanes", "bike_lanes.geojson", [{"cycleway": True}, {"highway": "cycleway"}]),
        (
            "transit stops",
            "transit_stops.geojson",
            [{"highway": "bus_stop"}, {"public_transport": "stop_position"}],
        ),
        ("schools", "schools.geojson", [{"amenity": "school"}]),
        ("grocery stores", "grocery.geojson", [{"shop": ["supermarket", "grocery"]}]),
    ]

    for name, filename, tags in layers:
        _run_layer(name, filename, tags, boundary)


if __name__ == "__main__":
    main()

