"""Compute tract-level walkability and amenity access scores for A2GeoLens."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
from pygris import tracts


PLACE = "Ann Arbor, Michigan, USA"
WGS84 = "EPSG:4326"
ANALYSIS_CRS = "EPSG:3078"
PARK_ACCESS_METERS = 800
TRACT_OVERLAP_THRESHOLD = 0.25
TRANSIT_DEDUPE_METERS = 10

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"


def _empty_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[], crs=WGS84)


def _read_optional(path: Path, label: str) -> gpd.GeoDataFrame:
    if not path.exists():
        print(f"warning: missing {label}: {path}")
        return _empty_gdf()
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:
        print(f"warning: could not read {label}: {exc}")
        return _empty_gdf()
    if "geometry" not in gdf.columns:
        return _empty_gdf()
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(WGS84)


def _write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_crs(WGS84).to_file(path, driver="GeoJSON")


def _load_or_fetch_boundary() -> gpd.GeoDataFrame:
    path = RAW_DIR / "ann_arbor_boundary.geojson"
    boundary = _read_optional(path, "Ann Arbor boundary")
    if not boundary.empty:
        return boundary

    print("Fetching Ann Arbor boundary because data/raw/ann_arbor_boundary.geojson is missing...")
    boundary = ox.geocode_to_gdf(PLACE).to_crs(WGS84)
    _write_geojson(boundary, path)
    return boundary


def _tract_name_column(gdf: gpd.GeoDataFrame) -> str | None:
    for column in ("NAMELSAD", "NAME", "GEOID"):
        if column in gdf.columns:
            return column
    return None


def build_tracts(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    output_path = RAW_DIR / "tracts_ann_arbor.geojson"
    if output_path.exists():
        tracts_gdf = _read_optional(output_path, "Ann Arbor tracts")
        if not tracts_gdf.empty:
            print(f"Loaded {len(tracts_gdf):,} Ann Arbor tracts from data/raw/tracts_ann_arbor.geojson")
            return tracts_gdf

    print("Fetching 2020 Washtenaw County census tracts with pygris...")
    tracts_gdf = tracts(state="MI", county="Washtenaw", year=2020, cb=True)
    tracts_gdf = tracts_gdf.to_crs(WGS84)

    tracts_m = tracts_gdf.to_crs(ANALYSIS_CRS)
    boundary_m = boundary.to_crs(ANALYSIS_CRS)
    city_geom = boundary_m.geometry.union_all()

    centroid_in_city = tracts_m.geometry.centroid.within(city_geom)
    overlap_area = tracts_m.geometry.intersection(city_geom).area
    tract_area = tracts_m.geometry.area.replace(0, pd.NA)
    overlap_ratio = overlap_area / tract_area

    selected = tracts_gdf[centroid_in_city | (overlap_ratio >= TRACT_OVERLAP_THRESHOLD)].copy()
    selected = selected.reset_index(drop=True)
    selected["tract_id"] = selected.get("GEOID", selected.index.astype(str)).astype(str)

    name_column = _tract_name_column(selected)
    if name_column and name_column != "tract_label":
        selected["tract_label"] = selected[name_column].astype(str)

    _write_geojson(selected, output_path)
    print(f"Saved {len(selected):,} Ann Arbor tracts -> data/raw/tracts_ann_arbor.geojson")
    return selected


def _ensure_tract_id(tracts_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    tracts_gdf = tracts_gdf.copy()
    if "tract_id" not in tracts_gdf.columns:
        if "GEOID" in tracts_gdf.columns:
            tracts_gdf["tract_id"] = tracts_gdf["GEOID"].astype(str)
        else:
            tracts_gdf["tract_id"] = tracts_gdf.index.astype(str)
    return tracts_gdf


def _filter_geometry(gdf: gpd.GeoDataFrame, geometry_types: tuple[str, ...]) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    return gdf[gdf.geometry.geom_type.isin(geometry_types)].copy()


def _dedupe_transit_stops(transit: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if transit.empty:
        return transit

    transit = transit.copy()
    transit["geometry"] = transit.geometry.representative_point()

    for column_set in (("element_type", "osmid"), ("osmid",)):
        columns = [column for column in column_set if column in transit.columns]
        if columns:
            transit = transit.drop_duplicates(subset=columns)
            break

    transit["snap_x"] = (transit.geometry.x / TRANSIT_DEDUPE_METERS).round().astype(int)
    transit["snap_y"] = (transit.geometry.y / TRANSIT_DEDUPE_METERS).round().astype(int)
    transit = transit.drop_duplicates(subset=["snap_x", "snap_y"])
    return transit.drop(columns=["snap_x", "snap_y"])


def _count_parks_near_tracts(tracts_m: gpd.GeoDataFrame, parks_m: gpd.GeoDataFrame) -> pd.Series:
    if parks_m.empty:
        return pd.Series(0, index=tracts_m["tract_id"])

    buffers = tracts_m[["tract_id", "geometry"]].copy()
    buffers["geometry"] = buffers.geometry.buffer(PARK_ACCESS_METERS)
    parks = parks_m[["geometry"]].reset_index(drop=True).copy()
    parks["park_id"] = parks.index

    joined = gpd.sjoin(parks, buffers, predicate="intersects", how="inner")
    counts = joined.drop_duplicates(subset=["park_id", "tract_id"]).groupby("tract_id").size()
    return counts.reindex(tracts_m["tract_id"], fill_value=0)


def _count_transit_in_tracts(tracts_m: gpd.GeoDataFrame, transit_m: gpd.GeoDataFrame) -> pd.Series:
    if transit_m.empty:
        return pd.Series(0, index=tracts_m["tract_id"])

    transit = _dedupe_transit_stops(transit_m)
    joined = gpd.sjoin(transit[["geometry"]], tracts_m[["tract_id", "geometry"]], predicate="within", how="inner")
    counts = joined.groupby("tract_id").size()
    return counts.reindex(tracts_m["tract_id"], fill_value=0)


def _bike_lengths_by_tract(tracts_m: gpd.GeoDataFrame, bikes_m: gpd.GeoDataFrame) -> pd.Series:
    if bikes_m.empty:
        return pd.Series(0.0, index=tracts_m["tract_id"])

    bikes = _filter_geometry(bikes_m, ("LineString", "MultiLineString"))
    if bikes.empty:
        return pd.Series(0.0, index=tracts_m["tract_id"])

    intersections = gpd.overlay(
        bikes[["geometry"]],
        tracts_m[["tract_id", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return pd.Series(0.0, index=tracts_m["tract_id"])

    intersections["length_m"] = intersections.geometry.length
    lengths = intersections.groupby("tract_id")["length_m"].sum()
    return lengths.reindex(tracts_m["tract_id"], fill_value=0.0)


def _nearest_grocery_distance(tracts_m: gpd.GeoDataFrame, grocery_m: gpd.GeoDataFrame) -> pd.Series:
    if grocery_m.empty:
        return pd.Series(pd.NA, index=tracts_m["tract_id"], dtype="Float64")

    groceries = grocery_m[["geometry"]].copy()
    groceries["geometry"] = groceries.geometry.representative_point()
    centroids = tracts_m[["tract_id", "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.centroid

    nearest = gpd.sjoin_nearest(
        centroids,
        groceries,
        how="left",
        distance_col="nearest_grocery_m",
    )
    distances = nearest.drop_duplicates(subset=["tract_id"]).set_index("tract_id")["nearest_grocery_m"]
    return distances.reindex(tracts_m["tract_id"])


def _normalize(series: pd.Series, invert: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.notna().sum() == 0:
        return pd.Series(0.0, index=series.index)

    if invert:
        values = values.max() - values

    minimum = values.min(skipna=True)
    maximum = values.max(skipna=True)
    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        fill_value = 1.0 if maximum and maximum > 0 else 0.0
        return pd.Series(fill_value, index=series.index)

    return ((values - minimum) / (maximum - minimum)).fillna(0.0)


def compute_scores() -> gpd.GeoDataFrame:
    boundary = _load_or_fetch_boundary()
    tracts_gdf = _ensure_tract_id(build_tracts(boundary))

    parks = _read_optional(RAW_DIR / "parks.geojson", "parks")
    transit = _read_optional(RAW_DIR / "transit_stops.geojson", "transit stops")
    bikes = _read_optional(RAW_DIR / "bike_lanes.geojson", "bike lanes")
    grocery = _read_optional(RAW_DIR / "grocery.geojson", "grocery stores")

    tracts_m = tracts_gdf.to_crs(ANALYSIS_CRS)
    parks_m = parks.to_crs(ANALYSIS_CRS) if not parks.empty else parks
    transit_m = transit.to_crs(ANALYSIS_CRS) if not transit.empty else transit
    bikes_m = bikes.to_crs(ANALYSIS_CRS) if not bikes.empty else bikes
    grocery_m = grocery.to_crs(ANALYSIS_CRS) if not grocery.empty else grocery

    metrics = pd.DataFrame(index=tracts_m["tract_id"])
    metrics["park_count_800m"] = _count_parks_near_tracts(tracts_m, parks_m).astype(int)
    metrics["transit_stops_in_tract"] = _count_transit_in_tracts(tracts_m, transit_m).astype(int)
    metrics["bike_lane_meters"] = _bike_lengths_by_tract(tracts_m, bikes_m).astype(float)
    metrics["nearest_grocery_m"] = _nearest_grocery_distance(tracts_m, grocery_m).astype("Float64")

    normalized = pd.DataFrame(index=metrics.index)
    normalized["park_score"] = _normalize(metrics["park_count_800m"])
    normalized["transit_score"] = _normalize(metrics["transit_stops_in_tract"])
    normalized["bike_score"] = _normalize(metrics["bike_lane_meters"])
    normalized["grocery_score"] = _normalize(metrics["nearest_grocery_m"], invert=True)

    metrics["walkability_score"] = (normalized.mean(axis=1) * 100).round(2)

    scored = tracts_gdf.merge(metrics.reset_index(), on="tract_id", how="left")
    return scored.to_crs(WGS84)


def print_summary(scored: gpd.GeoDataFrame) -> None:
    label_column = "tract_label" if "tract_label" in scored.columns else "tract_id"
    columns = [
        label_column,
        "walkability_score",
        "park_count_800m",
        "transit_stops_in_tract",
        "bike_lane_meters",
        "nearest_grocery_m",
    ]
    table = scored[columns].sort_values("walkability_score", ascending=False)

    print("\nTop 5 tracts by walkability score")
    print(table.head(5).to_string(index=False))

    print("\nBottom 5 tracts by walkability score")
    print(table.tail(5).sort_values("walkability_score").to_string(index=False))


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    scored = compute_scores()
    processed_path = PROCESSED_DIR / "tracts_scored.geojson"
    docs_path = DOCS_DATA_DIR / "tracts_scored.geojson"

    _write_geojson(scored, processed_path)
    _write_geojson(scored, docs_path)

    print(f"\nSaved scored tracts -> {processed_path.relative_to(PROJECT_ROOT)}")
    print(f"Saved web map data -> {docs_path.relative_to(PROJECT_ROOT)}")
    print_summary(scored)


if __name__ == "__main__":
    main()

