"""Render portfolio screenshots from generated GeoJSON without extra graphics deps."""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = PROJECT_ROOT / "docs" / "data"
SCREENSHOTS = PROJECT_ROOT / "docs" / "screenshots"
WIDTH = 1400
HEIGHT = 850
PADDING = 72

PAPER = (247, 244, 236)
INK = (24, 32, 31)
PARK = (87, 153, 93)
BIKE = (223, 132, 52)
TRANSIT = (44, 105, 174)
GROCERY = (166, 64, 40)
SCHOOL = (112, 91, 166)
WATER = (156, 190, 204)
VIRIDIS = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]


def read_geojson(name: str) -> dict:
    return json.loads((DOCS_DATA / name).read_text(encoding="utf-8"))


def write_js_data_bundles() -> None:
    for src in DOCS_DATA.glob("*.geojson"):
        variable_name = "A2GEOLENS_" + src.stem.upper().replace("-", "_")
        data = json.loads(src.read_text(encoding="utf-8"))
        src.with_suffix(".js").write_text(
            f"window.{variable_name} = {json.dumps(data, separators=(',', ':'))};\n",
            encoding="utf-8",
        )


def iter_coords(geometry: dict):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Point":
        yield tuple(coords[:2])
    elif gtype in {"LineString", "MultiPoint"}:
        for coord in coords:
            yield tuple(coord[:2])
    elif gtype in {"Polygon", "MultiLineString"}:
        for part in coords:
            for coord in part:
                yield tuple(coord[:2])
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for coord in ring:
                    yield tuple(coord[:2])
    elif gtype == "GeometryCollection":
        for child in geometry.get("geometries", []):
            yield from iter_coords(child)


def bounds(*collections: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for collection in collections:
        for feature in collection.get("features", []):
            for x, y in iter_coords(feature.get("geometry") or {}):
                xs.append(float(x))
                ys.append(float(y))
    return min(xs), min(ys), max(xs), max(ys)


def make_projector(extent: tuple[float, float, float, float]):
    minx, miny, maxx, maxy = extent
    sx = (WIDTH - PADDING * 2) / (maxx - minx)
    sy = (HEIGHT - PADDING * 2) / (maxy - miny)
    scale = min(sx, sy)
    used_w = (maxx - minx) * scale
    used_h = (maxy - miny) * scale
    ox = (WIDTH - used_w) / 2
    oy = (HEIGHT - used_h) / 2

    def project(coord):
        x, y = coord
        return int(ox + (x - minx) * scale), int(HEIGHT - (oy + (y - miny) * scale))

    return project


def canvas(color=PAPER) -> bytearray:
    return bytearray(color * (WIDTH * HEIGHT))


def put(px: bytearray, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        idx = (y * WIDTH + x) * 3
        px[idx : idx + 3] = bytes(color)


def blend_put(px: bytearray, x: int, y: int, color: tuple[int, int, int], alpha: float) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        idx = (y * WIDTH + x) * 3
        px[idx : idx + 3] = bytes(
            int(px[idx + channel] * (1 - alpha) + color[channel] * alpha) for channel in range(3)
        )


def rect(px: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    for y in range(max(0, y0), min(HEIGHT, y1)):
        for x in range(max(0, x0), min(WIDTH, x1)):
            put(px, x, y, color)


def line(px: bytearray, p0, p1, color: tuple[int, int, int], width: int = 1, alpha: float = 1.0) -> None:
    x0, y0 = p0
    x1, y1 = p1
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    radius = max(0, width // 2)
    while True:
        for yy in range(y0 - radius, y0 + radius + 1):
            for xx in range(x0 - radius, x0 + radius + 1):
                blend_put(px, xx, yy, color, alpha)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def polygon(px: bytearray, pts: list[tuple[int, int]], color: tuple[int, int, int], alpha: float = 1.0) -> None:
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    for y in range(max(0, min(ys)), min(HEIGHT, max(ys) + 1)):
        xs = []
        for i, (x1, y1) in enumerate(pts):
            x2, y2 = pts[(i + 1) % len(pts)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if y2 != y1:
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs), 2):
            if i + 1 < len(xs):
                for x in range(max(0, math.floor(xs[i])), min(WIDTH, math.ceil(xs[i + 1]))):
                    blend_put(px, x, y, color, alpha)


def dot(px: bytearray, point: tuple[int, int], color: tuple[int, int, int], radius: int = 4) -> None:
    x, y = point
    for yy in range(y - radius, y + radius + 1):
        for xx in range(x - radius, x + radius + 1):
            if (xx - x) ** 2 + (yy - y) ** 2 <= radius**2:
                blend_put(px, xx, yy, color, 0.95)


def draw_geometry(px: bytearray, geometry: dict, project, color, *, width=1, alpha=1.0, point_radius=4) -> None:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Point":
        dot(px, project(coords[:2]), color, point_radius)
    elif gtype == "LineString":
        pts = [project(c[:2]) for c in coords]
        for a, b in zip(pts, pts[1:]):
            line(px, a, b, color, width, alpha)
    elif gtype == "MultiLineString":
        for part in coords:
            draw_geometry(px, {"type": "LineString", "coordinates": part}, project, color, width=width, alpha=alpha)
    elif gtype == "Polygon":
        if coords:
            polygon(px, [project(c[:2]) for c in coords[0]], color, alpha)
            ring = [project(c[:2]) for c in coords[0]]
            for a, b in zip(ring, ring[1:]):
                line(px, a, b, INK, 1, 0.65)
    elif gtype == "MultiPolygon":
        for part in coords:
            draw_geometry(px, {"type": "Polygon", "coordinates": part}, project, color, width=width, alpha=alpha)


def score_color(score: float) -> tuple[int, int, int]:
    if score >= 70:
        return VIRIDIS[4]
    if score >= 55:
        return VIRIDIS[3]
    if score >= 40:
        return VIRIDIS[2]
    if score >= 25:
        return VIRIDIS[1]
    return VIRIDIS[0]


def write_png(path: Path, px: bytearray) -> None:
    rows = []
    for y in range(HEIGHT):
        start = y * WIDTH * 3
        rows.append(b"\x00" + bytes(px[start : start + WIDTH * 3]))
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def draw_base(px: bytearray, title_band: tuple[int, int, int]) -> None:
    rect(px, 0, 0, WIDTH, 58, title_band)
    for x in range(28, 332, 18):
        rect(px, x, 22, x + 10, 34, PAPER)
    for x, color in enumerate(VIRIDIS):
        rect(px, WIDTH - 250 + x * 36, 22, WIDTH - 220 + x * 36, 34, color)


def render(filename: str, *, mode: str) -> None:
    tracts = read_geojson("tracts_scored.geojson")
    parks = read_geojson("parks.geojson")
    bikes = read_geojson("bike_lanes.geojson")
    transit = read_geojson("transit_stops.geojson")
    grocery = read_geojson("grocery.geojson")
    schools = read_geojson("schools.geojson")
    project = make_projector(bounds(tracts))
    px = canvas()
    draw_base(px, INK if mode != "felt" else (238, 241, 236))

    if mode in {"hero", "felt"}:
        for collection, color, alpha in [(parks, PARK, 0.42), (schools, SCHOOL, 0.88)]:
            for feature in collection.get("features", []):
                geom = feature.get("geometry") or {}
                if geom.get("type") == "Point":
                    draw_geometry(px, geom, project, color, point_radius=4)
                else:
                    draw_geometry(px, geom, project, color, alpha=alpha)

    for feature in tracts.get("features", []):
        props = feature.get("properties", {})
        color = score_color(float(props.get("walkability_score") or 0))
        draw_geometry(px, feature.get("geometry") or {}, project, color, alpha=0.72 if mode != "score" else 0.9)

    if mode in {"hero", "felt"}:
        for feature in bikes.get("features", []):
            draw_geometry(px, feature.get("geometry") or {}, project, BIKE, width=3 if mode == "hero" else 2, alpha=0.78)
        for feature in transit.get("features", []):
            point = next(iter(iter_coords(feature.get("geometry") or {})), None)
            if point:
                dot(px, project(point), TRANSIT, 4 if mode == "hero" else 3)
        for feature in grocery.get("features", []):
            point = next(iter(iter_coords(feature.get("geometry") or {})), None)
            if point:
                dot(px, project(point), GROCERY, 6)

    if mode == "felt":
        rect(px, 0, 58, 285, HEIGHT, (238, 241, 236))
        for y, color in [(116, VIRIDIS[3]), (170, PARK), (224, BIKE), (278, TRANSIT), (332, GROCERY)]:
            rect(px, 36, y, 76, y + 18, color)
            rect(px, 92, y + 3, 226, y + 12, (185, 191, 184))

    write_png(SCREENSHOTS / filename, px)


def main() -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    write_js_data_bundles()
    render("hero_map.png", mode="hero")
    render("access_score.png", mode="score")
    render("felt_preview.png", mode="felt")
    print("Rendered screenshots to docs/screenshots/")


if __name__ == "__main__":
    main()
