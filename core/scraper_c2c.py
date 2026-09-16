import json
import math
import requests

C2C_API_URL = "https://api.camptocamp.org/routes"

def wgs84_to_epsg3857(lon: float, lat: float):
    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return int(x), int(y)

def epsg3857_to_wgs84(x: float, y: float):
    lon = (x / 20037508.34) * 180.0
    lat = (y / 20037508.34) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return round(lat, 5), round(lon, 5)

def normalize_point(pt: list) -> list:
    x, y = pt[0], pt[1]
    if -180.0 <= x <= 180.0 and -90.0 <= y <= 90.0:
        return [round(y, 5), round(x, 5)]
    lat, lon = epsg3857_to_wgs84(x, y)
    return [lat, lon]

def search_routes(bbox: list, activity: str = "trail") -> list:
    min_lon, min_lat, max_lon, max_lat = bbox

    min_x, min_y = wgs84_to_epsg3857(min_lon, min_lat)
    max_x, max_y = wgs84_to_epsg3857(max_lon, max_lat)

    act_param = (
        "hiking,mountain_climbing,snow_ice_mixed,snowshoeing"
        if activity == "trail"
        else "skitouring,snow_ice_mixed,mountain_climbing"
    )

    params = {
        "bbox": f"{min_x},{min_y},{max_x},{max_y}",
        "act": act_param,
        "limit": 100
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MountainScout/3.0",
        "Accept": "application/json"
    }

    routes = []
    try:
        resp = requests.get(C2C_API_URL, params=params, headers=headers, timeout=(4.0, 15.0))
        if resp.status_code != 200:
            return []

        documents = resp.json().get("documents", [])

        for doc in documents:
            doc_id = doc.get("document_id")

            locales = doc.get("locales", [])
            loc = next((l for l in locales if l.get("lang") == "fr"), locales[0] if locales else {})
            title = loc.get("title", f"Itinéraire Camptocamp #{doc_id}")

            gain = doc.get("elevation_up")
            loss = doc.get("elevation_down")
            max_alt = doc.get("elevation_max")
            min_alt = doc.get("elevation_min")

            if max_alt is None and min_alt is None:
                max_alt = 2600
                min_alt = 1600
            elif max_alt is None:
                max_alt = min_alt + (gain or 800)
            elif min_alt is None:
                min_alt = max(400, max_alt - (gain or 800))

            if gain is None:
                gain = max(100, max_alt - min_alt)
            if loss is None:
                loss = gain

            raw_geom = doc.get("geometry", {}).get("geom")
            geom = json.loads(raw_geom) if isinstance(raw_geom, str) else raw_geom

            coords = []
            elevations = []
            point_marker = None
            has_track = False

            if geom and isinstance(geom, dict):
                g_type = geom.get("type")
                g_coords = geom.get("coordinates", [])

                if g_type == "LineString" and len(g_coords) >= 2:
                    coords = [normalize_point(pt) for pt in g_coords]
                    has_track = True
                    if len(g_coords[0]) > 2 and g_coords[0][2] is not None:
                        elevations = [round(float(pt[2]), 1) for pt in g_coords]

                elif g_type == "MultiLineString" and g_coords:
                    for line in g_coords:
                        if len(line) >= 2:
                            coords.extend([normalize_point(pt) for pt in line])
                    if len(coords) >= 2:
                        has_track = True

                elif g_type == "Point" and len(g_coords) >= 2:
                    point_marker = normalize_point(g_coords)

            if has_track and (not elevations or len(elevations) != len(coords)):
                elevations = [
                    round(min_alt + (max_alt - min_alt) * (i / max(1, len(coords) - 1)), 1)
                    for i in range(len(coords))
                ]

            if not point_marker and coords:
                point_marker = coords[0]

            rating = (
                doc.get("hiking_rating")
                or doc.get("global_rating")
                or doc.get("ski_rating")
                or "Non coté"
            )

            summary = loc.get("summary") or loc.get("description") or "Itinéraire extrait de Camptocamp."
            if len(summary) > 400:
                summary = summary[:400] + "..."

            routes.append({
                "id": doc_id,
                "title": title,
                "rating": rating,
                "elevation_gain": int(gain),
                "elevation_loss": int(loss),
                "elevation_max": int(max_alt),
                "elevation_min": int(min_alt),
                "source_url": f"https://www.camptocamp.org/routes/{doc_id}",
                "summary": summary,
                "has_track": has_track,
                "coords": coords,
                "elevations": elevations,
                "point_marker": point_marker
            })

    except Exception:
        return []

    # Tri : les itinéraires possédant une vraie trace GPS arrivent en premier
    routes.sort(key=lambda r: (not r["has_track"], -r.get("elevation_gain", 0)))
    return routes