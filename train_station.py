#!/usr/bin/env python3
"""
train-station.py — Full-screen train enthusiast kiosk for Raspberry Pi
Displays a live map of trains, schedules, and train facts.
"""

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: CONFIG  (edit these to customize your installation)
# ═══════════════════════════════════════════════════════════════════

ORIGIN_LAT = 39.4143        # Frederick, MD
ORIGIN_LON = -77.4105

MAP_RADIUS_MILES = 200      # radius around origin to display
SCHEDULE_RADIUS_MILES = 50  # nearby stations to show in schedule panel

SCREEN_W = 1920
SCREEN_H = 1080
FPS_CAP = 30

TRAIN_UPDATE_SEC = 60       # how often to refresh train positions
SCHEDULE_UPDATE_SEC = 60    # how often to refresh schedules
MOTD_ROTATE_SEC = 30        # how often to cycle train fact
SCHEDULE_PAGE_ROTATE_SEC = 10  # how often to flip Train Information pages

MAP_PANEL_W = int(SCREEN_W * 0.70)   # 1344 px
SIDE_PANEL_W = SCREEN_W - MAP_PANEL_W  # 576 px
BOTTOM_PANEL_H = 90
PANEL_GAP = 16

TILE_SIZE = 256             # OSM tile size in pixels
TILE_ZOOM = 9               # zoom level (9 zooms in a bit tighter on the origin area)

OSM_TILE_URL = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
)

TILE_CACHE_DIR = "~/.cache/train-station/tiles"   # expanded after os import

# ── Colors ──────────────────────────────────────────────────────────
C_BG          = (10,  14,  20)
C_PANEL_BG    = (18,  24,  32)
C_PANEL_BORDER= (40,  60,  80)
C_HEADER_BG   = (20,  30,  45)
C_TEXT        = (210, 220, 230)
C_TEXT_DIM    = (110, 130, 150)
C_ACCENT      = (80,  180, 255)
C_ACCENT2     = (255, 200,  50)
C_TRAIN_DOT   = (255, 240,  80)
C_STATION_DOT = (255,  80,  80)
C_TRACK       = (100, 200, 100)
C_SEPARATOR   = (35,  50,  65)
C_MOTD_BG     = (15,  22,  35)
C_MOTD_BORDER = (60,  90, 120)

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: IMPORTS
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import math
import time
import random
import json
import threading
import hashlib
import io
from pathlib import Path
from collections import OrderedDict

import base64
import subprocess
import tempfile

import pygame
import requests
from PIL import Image

# ═══════════════════════════════════════════════════════════════════
# SECTION 3: MOTD FACTS  (50+ short train facts)
# ═══════════════════════════════════════════════════════════════════

MOTD_FACTS = [
    "The first steam locomotive, Rocket, reached 29 mph in 1829 — a world record at the time.",
    "The Trans-Siberian Railway spans 5,772 miles and crosses eight time zones.",
    "US freight trains move 1 ton of cargo 479 miles on a single gallon of fuel.",
    "The fastest commercial train is the Shanghai Maglev, hitting 267 mph in regular service.",
    "Baltimore & Ohio Railroad, opened in 1830, was the first US common-carrier railroad.",
    "A standard freight train can be over 2 miles long and carry 500+ railcars.",
    "The 'Big Boy' steam locomotive weighed 1.2 million pounds — the heaviest ever built.",
    "Japan's Shinkansen bullet trains have carried 10 billion passengers with zero fatal accidents.",
    "Train whistles follow a specific code: two longs, one short, one long means 'approaching crossing'.",
    "Railroad tracks are spaced 4 ft 8.5 in apart — the 'standard gauge' used worldwide.",
    "The B&O Railroad Museum in Baltimore houses the world's oldest collection of American locomotives.",
    "The MARC Penn Line connects Frederick to Washington D.C., running along a pre-Civil War route.",
    "Amtrak's Capitol Limited passes through the mid-Atlantic region on its Chicago–D.C. run daily.",
    "Railroad spikes hold rails to wooden ties; a typical mile of track needs 4,000 spikes.",
    "Locomotive headlights must be visible for at least 500 feet in the US.",
    "The term 'deadline' comes from the railroad: a train that passed its scheduled time was considered 'dead'.",
    "Train engineers communicate with hand signals that date back to the 1800s.",
    "Steel rails expand in heat — expansion joints prevent buckling on hot summer days.",
    "A red signal light has meant 'stop' on railways since the 1830s.",
    "CSX Transportation operates over 21,000 miles of track in the eastern United States.",
    "Norfolk Southern's Crescent Corridor passes through the Shenandoah Valley just west of Frederick.",
    "Railway bridges are built to support at least four times the load they normally carry.",
    "The 'deadman's switch' automatically stops a train if the engineer becomes incapacitated.",
    "Diesel-electric locomotives use diesel engines to generate electricity that powers traction motors.",
    "Positive Train Control (PTC) technology automatically stops trains to prevent collisions.",
    "The 1869 Golden Spike ceremony linked the US transcontinental railroad at Promontory Summit, Utah.",
    "A locomotive horn must sound at every public road crossing in the US.",
    "Freight trains use dynamic braking — the motors act as generators to slow the train.",
    "Rail is made from steel with very precise carbon content for strength and flexibility.",
    "Track geometry cars ride the rails measuring tiny imperfections invisible to the naked eye.",
    "The caboose, once mandatory on US freight trains, was phased out by the 1990s.",
    "Hot box detectors along the track sense overheating bearings before they cause derailments.",
    "A fully loaded coal train can weigh 15,000 tons — 30 million pounds.",
    "Train wheels have a slight taper (conical shape) that keeps them centered on the rails.",
    "The first American passenger train, Tom Thumb, lost a famous race to a horse in 1830.",
    "Pullman sleeping cars transformed long-distance travel when they debuted in the 1860s.",
    "The Chesapeake & Ohio Canal, running along the Potomac near Frederick, was once the railroad's rival.",
    "Grade crossings in the US are identified by a unique USDOT code for emergency reporting.",
    "An automatic coupler (Janney coupler) replaced dangerous link-and-pin couplers in the 1880s.",
    "Railroad workers once used flags, lanterns, and flares as the main signaling system.",
    "The Horseshoe Curve in Altoona, PA, is a National Historic Landmark for railroad engineering.",
    "Intermodal shipping containers can move from ship to rail to truck without unpacking cargo.",
    "The longest train ever recorded stretched 4.57 miles and carried iron ore in Australia.",
    "Steam locomotives require a fireman to shovel coal and manage the boiler — a skilled craft.",
    "Many vintage steam locomotives still run on heritage railways and excursion trains across the US.",
    "The railroad industry employs over 160,000 people in the United States today.",
    "Wheel flanges (the lip on the inner edge) keep train wheels from slipping off the rails.",
    "A locomotive's tractive effort — the pulling force — can exceed 200,000 pounds.",
    "Wooden railroad ties are gradually being replaced with concrete and composite alternatives.",
    "Radio communication replaced telegraph along the rails, but the track circuit still signals occupancy.",
    "The Appalachian Mountains forced early railroad builders to use dramatic switchbacks and tunnels.",
    "Electrified rail corridors in the Northeast Corridor allow the Acela to reach 150 mph.",
    "Train bells are rung when the train is moving at low speeds near stations and crossings.",
    "The Strasburg Rail Road in PA, founded in 1832, is the oldest continuously operating railroad in the US.",
    "Retarders in rail yards use friction or electromagnets to slow individual railcars being sorted.",
    "A unit train carries only one type of commodity — coal, grain, or autos — with no mixed cars.",
]

# ═══════════════════════════════════════════════════════════════════
# SECTION 4: UTILITY — GEO / MATH HELPERS
# ═══════════════════════════════════════════════════════════════════

def haversine_miles(lat1, lon1, lat2, lon2):
    """Return distance in miles between two lat/lon points."""
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def latlon_to_tile(lat, lon, zoom):
    """Convert lat/lon to tile (x, y) at the given zoom level."""
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return x, y

def tile_to_latlon(x, y, zoom):
    """Convert tile (x, y) to lat/lon of the NW corner."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_r)
    return lat, lon

def latlon_to_pixel(lat, lon, origin_tile_x, origin_tile_y, zoom, surface_origin_px):
    """
    Convert lat/lon to pixel coordinates on the map surface.
    surface_origin_px: (px, py) pixel offset of origin_tile_x/y on the surface.
    """
    tx, ty = latlon_to_tile(lat, lon, zoom)
    # fractional tile position
    lat_r = math.radians(lat)
    n = 2 ** zoom
    fx = (lon + 180.0) / 360.0 * n
    fy = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    px = surface_origin_px[0] + (fx - origin_tile_x) * TILE_SIZE
    py = surface_origin_px[1] + (fy - origin_tile_y) * TILE_SIZE
    return int(px), int(py)

def bbox_from_origin(lat, lon, radius_miles):
    """Return (min_lat, min_lon, max_lat, max_lon) for a square bounding box."""
    d_lat = radius_miles / 69.0
    d_lon = radius_miles / (69.0 * math.cos(math.radians(lat)))
    return (lat - d_lat, lon - d_lon, lat + d_lat, lon + d_lon)

def _parse_hex_color(color_hex: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not color_hex or not isinstance(color_hex, str) or len(color_hex) != 7 or not color_hex.startswith("#"):
        return fallback
    try:
        return (int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16))
    except Exception:
        return fallback

# ═══════════════════════════════════════════════════════════════════
# SECTION 5: TILE CACHE
# ═══════════════════════════════════════════════════════════════════

class TileCache:
    """Downloads and caches map tiles to disk. Thread-safe LRU in-memory cache."""

    MAX_MEMORY = 300  # max tiles in memory

    def __init__(self, cache_dir=TILE_CACHE_DIR):
        self.cache_dir = Path(os.path.expanduser(cache_dir))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._mem: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "TrainStationKiosk/1.0 (train enthusiast display; contact: kiosk@local)"
        })

    def _tile_path(self, url_template, z, x, y):
        key = f"{url_template}_{z}_{x}_{y}"
        hsh = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / hsh[:2] / (hsh + ".png")

    def _mem_key(self, url_template, z, x, y):
        return (url_template, z, x, y)

    def get(self, url_template, z, x, y) -> pygame.Surface | None:
        """Return a pygame Surface for the tile, or None if unavailable."""
        mk = self._mem_key(url_template, z, x, y)
        with self._lock:
            if mk in self._mem:
                self._mem.move_to_end(mk)
                return self._mem[mk]

        # try disk cache
        path = self._tile_path(url_template, z, x, y)
        if path.exists():
            surf = self._load_png_surface(path)
            if surf:
                self._store_mem(mk, surf)
                return surf

        # fetch from network
        url = url_template.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(resp.content)
                surf = self._load_png_surface(path)
                if surf:
                    self._store_mem(mk, surf)
                    return surf
        except Exception:
            pass
        return None

    def _load_png_surface(self, path) -> pygame.Surface | None:
        try:
            img = Image.open(path).convert("RGBA")
            data = img.tobytes()
            surf = pygame.image.fromstring(data, img.size, "RGBA").convert_alpha()
            return surf
        except Exception:
            return None

    def _store_mem(self, key, surf):
        with self._lock:
            self._mem[key] = surf
            self._mem.move_to_end(key)
            while len(self._mem) > self.MAX_MEMORY:
                self._mem.popitem(last=False)

    def prefetch(self, url_template, z, x_range, y_range):
        """Background prefetch of a tile grid."""
        def _fetch():
            for x in x_range:
                for y in y_range:
                    self.get(url_template, z, x, y)
                    time.sleep(0.05)   # be polite to tile servers
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()

# ═══════════════════════════════════════════════════════════════════
# SECTION 6: OVERPASS CLIENT
# ═══════════════════════════════════════════════════════════════════

class OverpassClient:
    """Fetches railway and station data from the Overpass API with caching."""

    INFRA_CACHE_SEC = 600    # 10 minutes for static infrastructure
    INFRA_EMPTY_RETRY_SEC = 20  # retry quickly when infrastructure comes back empty
    TRAIN_CACHE_SEC = 60     # 60 seconds for train positions

    def __init__(self):
        self._infra_cache = None
        self._infra_ts = 0
        self._infra_bbox_key = None
        self._train_cache = None
        self._train_ts = 0
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "TrainStationKiosk/1.0 (train enthusiast display; contact: kiosk@local)",
            "Accept": "application/json",
        })

    def _query(self, ql: str) -> dict | None:
        for endpoint in OVERPASS_URLS:
            try:
                resp = self._session.post(
                    endpoint,
                    data={"data": ql},
                    timeout=40
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
        return None

    def get_infrastructure(self, bbox):
        """
        Returns dict with 'tracks' (list of way node-lists) and 'stations' (list of nodes).
        bbox = (min_lat, min_lon, max_lat, max_lon)
        """
        bbox_key = tuple(round(v, 4) for v in bbox)
        now = time.time()
        with self._lock:
            if self._infra_cache:
                cache_age = now - self._infra_ts
                has_tracks = bool(self._infra_cache.get("tracks"))
                if has_tracks and cache_age < self.INFRA_CACHE_SEC and self._infra_bbox_key == bbox_key:
                    return self._infra_cache
                if (not has_tracks) and cache_age < self.INFRA_EMPTY_RETRY_SEC and self._infra_bbox_key == bbox_key:
                    return self._infra_cache

        min_lat, min_lon, max_lat, max_lon = bbox
        ql = f"""
[out:json][timeout:60];
(
  way["railway"="rail"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["railway"="station"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["railway"="halt"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out body geom;
"""
        data = self._query(ql)
        result = self._parse_infrastructure(data)
        if not result["tracks"]:
            # Fallback: query smaller boxes to reduce Overpass timeouts and recover rail geometry.
            merged = {"tracks": [], "stations": []}
            for sb in self._split_bbox(min_lat, min_lon, max_lat, max_lon):
                smin_lat, smin_lon, smax_lat, smax_lon = sb
                ql_small = f"""
[out:json][timeout:40];
(
  way["railway"="rail"]({smin_lat},{smin_lon},{smax_lat},{smax_lon});
  node["railway"="station"]({smin_lat},{smin_lon},{smax_lat},{smax_lon});
  node["railway"="halt"]({smin_lat},{smin_lon},{smax_lat},{smax_lon});
);
out body geom;
"""
                part = self._parse_infrastructure(self._query(ql_small))
                merged["tracks"].extend(part["tracks"])
                merged["stations"].extend(part["stations"])
            result = self._dedupe_infrastructure(merged)

        with self._lock:
            if result.get("tracks"):
                self._infra_cache = result
                self._infra_ts = time.time()
                self._infra_bbox_key = bbox_key
            else:
                # Never let an empty fetch wipe out a previously good infrastructure cache.
                if not self._infra_cache:
                    self._infra_cache = result
                    self._infra_ts = time.time()
                    self._infra_bbox_key = bbox_key
        return result

    def _parse_infrastructure(self, data) -> dict:
        tracks = []
        stations = []
        if not data:
            return {"tracks": tracks, "stations": stations}

        node_coords = {}
        for el in data.get("elements", []):
            if el["type"] == "node":
                node_coords[el["id"]] = (el["lat"], el["lon"])
                tags = el.get("tags", {})
                if tags.get("railway") in ("station", "halt"):
                    stations.append({
                        "lat": el["lat"],
                        "lon": el["lon"],
                        "name": tags.get("name", ""),
                        "operator": tags.get("operator", ""),
                    })

        for el in data.get("elements", []):
            if el["type"] == "way" and el.get("tags", {}).get("railway") == "rail":
                geom = el.get("geometry", [])
                if geom:
                    pts = [(g["lat"], g["lon"]) for g in geom]
                else:
                    pts = [node_coords[n] for n in el.get("nodes", []) if n in node_coords]
                if len(pts) >= 2:
                    tracks.append({
                        "points": pts,
                        "name": el.get("tags", {}).get("name", ""),
                        "maxspeed": el.get("tags", {}).get("maxspeed", ""),
                    })

        return {"tracks": tracks, "stations": stations}

    def get_trains(self, bbox):
        """
        Returns list of train route relations that pass through the bounding box.
        Uses a tighter bbox around the origin for 'nearby' relevance.
        """
        now = time.time()
        with self._lock:
            if self._train_cache and now - self._train_ts < self.TRAIN_CACHE_SEC:
                return self._train_cache

        # Use the full map bbox so all on-screen routes are included
        d_lat = 200.0 / 69.0
        d_lon = 200.0 / (69.0 * math.cos(math.radians(ORIGIN_LAT)))
        min_lat = ORIGIN_LAT - d_lat
        max_lat = ORIGIN_LAT + d_lat
        min_lon = ORIGIN_LON - d_lon
        max_lon = ORIGIN_LON + d_lon

        ql = f"""
[out:json][timeout:45];
(
  relation["type"="route"]["route"="train"]({min_lat},{min_lon},{max_lat},{max_lon});
  relation["type"="route"]["route"="railway"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out tags;
"""
        data = self._query(ql)
        trains = self._parse_trains(data)

        with self._lock:
            self._train_cache = trains
            self._train_ts = time.time()
        return trains

    def _parse_trains(self, data) -> list:
        trains = []
        if not data:
            return trains
        seen = set()
        for el in data.get("elements", []):
            if el["type"] == "relation":
                tags = el.get("tags", {})
                name = tags.get("name", "")
                ref  = tags.get("ref", "")
                op   = tags.get("operator", "")
                frm  = tags.get("from", "")
                to   = tags.get("to", "")
                route_type = tags.get("route", "train")

                # De-duplicate by (operator, ref, from, to)
                key = (op, ref, frm, to)
                if key in seen:
                    continue
                seen.add(key)

                display = name or (f"{op} {ref}".strip()) or f"Route {el['id']}"
                trains.append({
                    "id": el["id"],
                    "name": display,
                    "operator": op,
                    "from": frm,
                    "to": to,
                    "ref": ref,
                    "route_type": route_type,
                    "colour": tags.get("colour", ""),
                    "network": tags.get("network", ""),
                })
        # Sort: named routes with both from/to first
        trains.sort(key=lambda r: (0 if r["from"] and r["to"] else 1, r["name"]))
        return trains

    def _split_bbox(self, min_lat, min_lon, max_lat, max_lon):
        mid_lat = (min_lat + max_lat) / 2.0
        mid_lon = (min_lon + max_lon) / 2.0
        return [
            (min_lat, min_lon, mid_lat, mid_lon),
            (min_lat, mid_lon, mid_lat, max_lon),
            (mid_lat, min_lon, max_lat, mid_lon),
            (mid_lat, mid_lon, max_lat, max_lon),
        ]

    def _dedupe_infrastructure(self, infra: dict) -> dict:
        tracks = []
        seen_tracks = set()
        for tr in infra.get("tracks", []):
            pts = tr.get("points", [])
            if len(pts) < 2:
                continue
            key = (round(pts[0][0], 5), round(pts[0][1], 5), round(pts[-1][0], 5), round(pts[-1][1], 5), len(pts))
            if key in seen_tracks:
                continue
            seen_tracks.add(key)
            tracks.append(tr)

        stations = []
        seen_stations = set()
        for st in infra.get("stations", []):
            key = (round(st.get("lat", 0.0), 5), round(st.get("lon", 0.0), 5), st.get("name", ""))
            if key in seen_stations:
                continue
            seen_stations.add(key)
            stations.append(st)
        return {"tracks": tracks, "stations": stations}

# ═══════════════════════════════════════════════════════════════════
# SECTION 6b: AMTRAKER CLIENT  (live train positions + schedules)
# ═══════════════════════════════════════════════════════════════════

# Known Amtrak station coordinates (lat, lon) for mid-Atlantic proximity checks
AMTRAK_STATION_COORDS = {
    "WAS": (38.8973, -77.0063, "Washington Union"),
    "BAL": (39.2841, -76.6227, "Baltimore Penn"),
    "BWI": (39.1771, -76.6688, "BWI Airport"),
    "NCR": (38.9478, -76.8738, "New Carrollton"),
    "RKV": (39.0839, -77.1528, "Rockville"),
    "ABE": (39.5094, -76.1713, "Aberdeen"),
    "WIL": (39.7369, -75.5513, "Wilmington"),
    "MRB": (39.4575, -77.9714, "Martinsburg"),
    "HFY": (39.3253, -77.7283, "Harpers Ferry"),
    "HAR": (40.2598, -76.8831, "Harrisburg"),
    "LNC": (40.0415, -76.3008, "Lancaster"),
    "PHL": (39.9566, -75.1822, "Philadelphia 30th St"),
    "ALX": (38.8056, -77.0583, "Alexandria"),
    "FBG": (38.3014, -77.4614, "Fredericksburg"),
    "CUM": (39.6481, -78.7606, "Cumberland"),
    "GAI": (39.1437, -77.2011, "Gaithersburg"),   # approx, not Amtrak
}

def station_distance_from_origin(station_code: str) -> float:
    """Return miles from ORIGIN to a known station, or 9999."""
    info = AMTRAK_STATION_COORDS.get(station_code)
    if not info:
        return 9999.0
    return haversine_miles(ORIGIN_LAT, ORIGIN_LON, info[0], info[1])


class AmtrakerClient:
    """
    Fetches live Amtrak train positions and schedules from the public
    Amtraker API (api-v3.amtraker.com). No API key required.
    """

    API_URL = "https://api-v3.amtraker.com/v3/trains"
    CACHE_SEC = 60
    EXCLUDED_ROUTE_KEYWORDS = (
        "metro", "subway", "light rail", "tram", "streetcar",
        "wmata", "mta", "mbta", "septa", "bart", "path",
    )

    def __init__(self):
        self._cache = None
        self._ts = 0
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "TrainStationKiosk/1.0"})

    def get_all_trains(self) -> list:
        """Return list of all active train dicts, refreshed every CACHE_SEC."""
        now = time.time()
        with self._lock:
            if self._cache is not None and now - self._ts < self.CACHE_SEC:
                return self._cache

        trains = self._fetch()
        with self._lock:
            self._cache = trains
            self._ts = time.time()
        return trains

    def get_trains_in_bbox(self, bbox) -> list:
        """Return only trains whose current position falls within bbox."""
        min_lat, min_lon, max_lat, max_lon = bbox
        return [
            t for t in self.get_all_trains()
            if self._is_mainline_passenger_train(t)
            and t.get("lat") and t.get("lon")
            and min_lat <= t["lat"] <= max_lat
            and min_lon <= t["lon"] <= max_lon
        ]

    def get_nearby_schedule(self, radius_miles: float = SCHEDULE_RADIUS_MILES) -> list:
        """
        Return schedule entries for upcoming stops at stations within radius_miles.
        Each entry: {train_num, route_name, station_name, station_code,
                     sch_dep, est_dep, status, delay_min, dist_miles,
                     destination, next_stop, direction, speed_mph}
        """
        from datetime import datetime, timezone, timedelta
        entries = []
        best_by_train_num = {}
        now_utc = datetime.now(timezone.utc)

        for train in self.get_all_trains():
            if not self._is_mainline_passenger_train(train):
                continue
            num = train.get("trainNum", "?")
            route = train.get("routeName", "")
            destination = self._get_destination_name(train)
            next_stop = self._get_next_stop_name(train)
            direction = (str(train.get("heading") or "")).upper().strip() or "?"
            try:
                speed_mph = max(0.0, float(train.get("velocity") or 0.0))
            except Exception:
                speed_mph = 0.0
            train_lat = train.get("lat")
            train_lon = train.get("lon")
            train_dist = None
            if train_lat and train_lon:
                train_dist = haversine_miles(ORIGIN_LAT, ORIGIN_LON, train_lat, train_lon)
                if train_dist > radius_miles:
                    continue

            best_entry = None
            for stop in train.get("stations", []):
                code = stop.get("code", "")
                station_dist = station_distance_from_origin(code)
                dist = station_dist if station_dist < 9999 else (train_dist if train_dist is not None else 9999.0)

                # use estimated departure if available, else scheduled
                dep_str = stop.get("dep") or stop.get("schDep") or ""
                sch_str = stop.get("schDep") or ""
                status  = stop.get("status", "")

                if not dep_str:
                    continue

                try:
                    dep_dt = datetime.fromisoformat(dep_str)
                    sch_dt = datetime.fromisoformat(sch_str) if sch_str else dep_dt
                    # skip stops that already departed more than 2 minutes ago
                    if dep_dt < now_utc and status == "Departed":
                        continue
                    delay_min = int((dep_dt - sch_dt).total_seconds() / 60)
                    candidate = {
                        "train_num":    num,
                        "route_name":   route,
                        "station_name": stop.get("name", code),
                        "station_code": code,
                        "sch_dep":      sch_dt,
                        "est_dep":      dep_dt,
                        "status":       status,
                        "delay_min":    delay_min,
                        "dist_miles":   dist,
                        "train_lat":    train_lat,
                        "train_lon":    train_lon,
                        "destination":  destination,
                        "next_stop":    next_stop,
                        "direction":    direction,
                        "speed_mph":    speed_mph,
                    }
                    if best_entry is None:
                        best_entry = candidate
                    else:
                        # Keep one row per train: earliest upcoming stop wins; distance breaks ties.
                        if (candidate["est_dep"], candidate["dist_miles"]) < (
                            best_entry["est_dep"], best_entry["dist_miles"]
                        ):
                            best_entry = candidate
                except Exception:
                    continue

            if best_entry is None and train_dist is not None:
                # Fallback row so visible trains without usable stop times still appear in Train Information.
                best_entry = {
                    "train_num":    num,
                    "route_name":   route,
                    "station_name": next_stop if next_stop != "—" else destination,
                    "station_code": "",
                    "sch_dep":      now_utc + timedelta(days=7),
                    "est_dep":      now_utc + timedelta(days=7),
                    "status":       "Enroute",
                    "delay_min":    0,
                    "dist_miles":   train_dist,
                    "train_lat":    train_lat,
                    "train_lon":    train_lon,
                    "destination":  destination,
                    "next_stop":    next_stop,
                    "direction":    direction,
                    "speed_mph":    speed_mph,
                }

            if best_entry is not None:
                tnum = str(best_entry.get("train_num", "?"))
                prev = best_by_train_num.get(tnum)
                if prev is None or (best_entry["est_dep"], best_entry["dist_miles"]) < (
                    prev["est_dep"], prev["dist_miles"]
                ):
                    best_by_train_num[tnum] = best_entry

        entries = list(best_by_train_num.values())
        # sort by estimated departure time
        entries.sort(key=lambda e: e["est_dep"])
        return entries

    def _fetch(self) -> list:
        try:
            resp = self._session.get(self.API_URL, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                trains = []
                for num, group in data.items():
                    for t in group:
                        trains.append(t)
                return trains
        except Exception:
            pass
        with self._lock:
            return self._cache if self._cache is not None else []

    def _is_mainline_passenger_train(self, train: dict) -> bool:
        route_name = str(train.get("routeName") or "").lower()
        if any(keyword in route_name for keyword in self.EXCLUDED_ROUTE_KEYWORDS):
            return False

        # Amtrak train numbers are numeric; filter out line-style IDs often used by metro systems.
        train_num = str(train.get("trainNum") or "").strip()
        if not any(ch.isdigit() for ch in train_num):
            return False

        return True

    def _get_destination_name(self, train: dict) -> str:
        for stop in reversed(train.get("stations", [])):
            name = (stop.get("name") or "").strip()
            if name:
                return name
        return str(train.get("routeName") or "").strip() or "Unknown"

    def _get_next_stop_name(self, train: dict) -> str:
        for stop in train.get("stations", []):
            status = (stop.get("status") or "").strip().lower()
            if status not in {"departed", "arrived", "completed", "cancelled"}:
                name = (stop.get("name") or stop.get("code") or "").strip()
                if name:
                    return name
        return "—"


# ═══════════════════════════════════════════════════════════════════
# SECTION 6c: TRAIN SPRITE — Noto Emoji 🚂 (U+1F682) CC BY 4.0
#   Source: https://github.com/googlefonts/noto-emoji
#   Loaded once at startup via rsvg-convert, tinted per route color.
# ═══════════════════════════════════════════════════════════════════

# Noto emoji 🚂 SVG embedded as base64 — no network needed at runtime
_TRAIN_SVG_B64 = (
    "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFk"
    "b2JlIElsbHVzdHJhdG9yIDI1LjIuMywgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246"
    "IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzYiIHhtbG5z"
    "PSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMu"
    "b3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAxMjggMTI4IiBz"
    "dHlsZT0iZW5hYmxlLWJhY2tncm91bmQ6bmV3IDAgMCAxMjggMTI4OyIgeG1sOnNwYWNlPSJwcmVz"
    "ZXJ2ZSI+CjxwYXRoIHN0eWxlPSJmaWxsOiNGNDQzMzY7IiBkPSJNMjIuNzMsOTkuNTNjLTIuMzUs"
    "MC4wMi00LjUzLDEuMjEtNS44MiwzLjE3TDQuODMsMTIxLjA4bDAuMDksMGMtMS4wOCwwLjAyLTEu"
    "OTUsMC44OS0xLjk1LDEuOTgKCXYwLjAyYzAsMC40MSwwLjMzLDAuNzQsMC43NCwwLjc0SDIxLjdj"
    "MC40MSwwLDAuNzQtMC4zMywwLjc0LTAuNzR2LTAuMDJjMC0wLjk2LTAuNjgtMS43Ni0xLjU4LTEu"
    "OTRsMS44NS0xMS40MkwyMi43Myw5OS41M3oiLz4KPHBhdGggc3R5bGU9Im9wYWNpdHk6MC44NTtm"
    "aWxsOiNCREJEQkQ7IiBkPSJNNDMuMzcsMjIuMmMyLjIxLDAuMDIsNC4wNywxLjczLDYuMjMsMi4x"
    "NmM4LjIyLDEuNjUsMTAuMi0yLjI0LDEyLjk4LTMuMDkKCWMyLjc4LTAuODUsNi43OCwyLjc3LDEz"
    "LjYxLTAuMjljMy41NS0xLjU5LDQuODQtNi40NSwzLjI1LTkuODZjLTAuNTItMS4xMi0zLjU3LTcu"
    "NTMtMTQuMzctNS45Yy0wLjgyLDAuMTItMS42MiwwLjM0LTIuNDIsMC41MwoJYy01LjY2LDEuMzUt"
    "OC4zMS0yLjc3LTE4LjgyLTAuOTdjLTE3LjIsMi45NC0xNi43NCwyMC4wNi0xNS4zMiwyMy4wNEMy"
    "OC41MSwyNy44MiwzNC4yNCwyMi4xLDQzLjM3LDIyLjJ6Ii8+CjxwYXRoIHN0eWxlPSJvcGFjaXR5"
    "OjAuNjU7ZmlsbDojRTBFMEUwOyIgZD0iTTI3LjAzLDguODljMy43OS0zLjYyLDEwLjUzLTQuNDks"
    "MTQuODEtMS40MmMwLjYzLDAuNDUsMS4yMywxLDIuMDEsMS4xOQoJYzAuNzUsMC4xOSwxLjU1LDAu"
    "MDIsMi4zMi0wLjFjMi45MS0wLjQzLDYuMTgsMC4xMiw4LjEzLDIuMThjMS45NSwyLjA2LDEuNzgs"
    "NS43MS0wLjcsNy4yYy00LjgxLDIuODgtOC42My0xLjE1LTE2Ljg0LDEuNgoJYy00LjkxLDEuNjUt"
    "OC4zNyw2LTkuNjksMTAuNzJDMjcuMDcsMzAuMjcsMTguMzEsMTcuMjIsMjcuMDMsOC44OXoiLz4K"
    "PHBhdGggc3R5bGU9ImZpbGw6IzQyNDI0MjsiIGQ9Ik00NC45OCwyMS43OWMwLTAuNTMtMC40My0w"
    "Ljk2LTAuOTYtMC45NkgxNy43M2MtMC41MywwLTAuOTYsMC40My0wLjk2LDAuOTZ2NS40NgoJYzIu"
    "MTEsNy44OSw3LjIsMTUuNDQsOC4xNywxNi44M3YxOS41OUgzNi44VjQ0LjA5YzAuOTQtMS4zLDUu"
    "NzUtOC4xOCw4LjE3LTE2Ljg0VjIxLjc5eiIvPgo8cG9seWdvbiBzdHlsZT0iZmlsbDojNDI0MjQy"
    "OyIgcG9pbnRzPSIxMjEuODcsODUuNDQgMTE1Ljk1LDg3LjczIDIyLjcsODcuNzMgMjIuNywxMDku"
    "NyAzMy4xNiwxMDkuNyAzMy4xNiwxMTcuNjYgNDguNDQsMTE3LjY2IAoJNDguNDQsMTA5LjcgMTIx"
    "Ljg3LDEwOS43ICIvPgo8cGF0aCBzdHlsZT0iZmlsbDojNDI0MjQyOyIgZD0iTTM5Ljg2LDg5LjQ4"
    "bC0xNy4xNi0wLjAxYzAsMCwwLjgtNi4yNiwwLjgtMTMuNzVTMjIuNjUsNjEuOSwyMi42NSw2MS45"
    "aDE2Ljc3CgljMCwwLDAuOTQsNC4wMiwwLjk0LDEzLjQyUzM5Ljg2LDg5LjQ4LDM5Ljg2LDg5LjQ4"
    "eiIvPgo8cGF0aCBzdHlsZT0iZmlsbDojMjEyMTIxOyIgZD0iTTU0LjQsOTguNDVoLTIuOTRjLTAu"
    "MS0yLjI4LTAuMzgtMy41MS0wLjc0LTQuMjNjLTAuMzItMC42Mi0wLjktMS4xLTEuNi0xLjEKCWMt"
    "MC41OCwwLTE2LjU0LDcuMDMtMTYuNTQsNy4wM2MwLDMuODgsMC43MSw3LjAzLDEuNTksNy4wM2Mw"
    "LDAsMTMsMCwxNC41OSwwYzIuMjEsMCwyLjY5LTIuMjUsMi43NC01LjdoMi4zNmwxOS42Nyw4LjMx"
    "bDYuMzIsMC4wNAoJTDU0LjQsOTguNDV6Ii8+Cjxwb2x5Z29uIHN0eWxlPSJmaWxsOiM2MDYwNjA7"
    "IiBwb2ludHM9IjEwMy4wMiw4OS40OCA3MC4wNSw4OS40OCA2OS41OSw2MS45IDc4LjIxLDU5LjIz"
    "IDc3Ljk5LDc0LjQxIDEwMy43NCw3NC40MSAiLz4KPHBhdGggc3R5bGU9ImZpbGw6IzAwNzk2Qjsi"
    "IGQ9Ik0zOS4zMSw4OS40OGwyOS4yLDBjMC42Ny0zLjQ0LDEuMzQtOC4yNCwxLjM0LTEzLjcyYzAt"
    "MTEuMDYtMS43NS0xMy44Ny0xLjc1LTEzLjg3SDUzLjExSDM5LjEKCWMwLDAsMC45MSw2LjM1LDAu"
    "OTEsMTMuODRDNDAuMDEsODMuMjMsMzkuMzEsODkuNDgsMzkuMzEsODkuNDh6Ii8+CjxnPgoJPGc+"
    "CgkJPHBhdGggc3R5bGU9ImZpbGw6IzU0NkU3QTsiIGQ9Ik01MC4wMywxMTIuMTZjMi4xNiwwLDMu"
    "OTIsMS43NiwzLjkyLDMuOTJTNTIuMTksMTIwLDUwLjAzLDEyMHMtMy45Mi0xLjc2LTMuOTItMy45"
    "MgoJCQlTNDcuODcsMTEyLjE2LDUwLjAzLDExMi4xNiBNNTAuMDMsMTA4LjE2Yy00LjM3LDAtNy45"
    "MiwzLjU1LTcuOTIsNy45MnMzLjU1LDcuOTIsNy45Miw3LjkyYzQuMzcsMCw3LjkyLTMuNTUsNy45"
    "Mi03LjkyCgkJCVM1NC40LDEwOC4xNiw1MC4wMywxMDguMTZMNTAuMDMsMTA4LjE2eiIvPgoJPC9n"
    "PgoJPGNpcmNsZSBzdHlsZT0iZmlsbDojRjQ0MzM2OyIgY3g9IjUwLjAzIiBjeT0iMTE2LjA4IiBy"
    "PSI0LjU4Ii8+CjwvZz4KPGc+Cgk8Zz4KCQk8cGF0aCBzdHlsZT0iZmlsbDojNTQ2RTdBOyIgZD0i"
    "TTMxLjU3LDExMi4xNmMyLjE2LDAsMy45MiwxLjc2LDMuOTIsMy45MlMzMy43MywxMjAsMzEuNTcs"
    "MTIwcy0zLjkyLTEuNzYtMy45Mi0zLjkyCgkJCVMyOS40MSwxMTIuMTYsMzEuNTcsMTEyLjE2IE0z"
    "MS41NywxMDguMTZjLTQuMzcsMC03LjkyLDMuNTUtNy45Miw3LjkyUzI3LjIsMTI0LDMxLjU3LDEy"
    "NHM3LjkyLTMuNTUsNy45Mi03LjkyCgkJCVMzNS45NSwxMDguMTYsMzEuNTcsMTA4LjE2TDMxLjU3"
    "LDEwOC4xNnoiLz4KCTwvZz4KCTxjaXJjbGUgc3R5bGU9ImZpbGw6I0Y0NDMzNjsiIGN4PSIzMS41"
    "NyIgY3k9IjExNi4wOCIgcj0iNC41OCIvPgo8L2c+CjxwYXRoIHN0eWxlPSJmaWxsOm5vbmU7c3Ry"
    "b2tlOiM2MDdEOEI7c3Ryb2tlLXdpZHRoOjM7c3Ryb2tlLW1pdGVybGltaXQ6MTA7IiBkPSJNMzYu"
    "ODIsMTA0Ljk4Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiNDNjI4Mjg7IiBkPSJNNzcuOTcsMzguOTR2"
    "NDQuNjdoNDQuMjNWMzguOTRINzcuOTd6IE0xMTcuNjcsNzcuOTdIODIuNTRWNDMuODVoMzUuMTJW"
    "NzcuOTd6Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiMyRjc4ODk7IiBkPSJNMjkuNDUsMjcuODVIMTku"
    "MjhWMjIuNGMwLTAuNTMsMC40My0wLjk2LDAuOTYtMC45Nmg4LjI1YzAuNTMsMCwwLjk2LDAuNDMs"
    "MC45NiwwLjk2VjI3Ljg1eiIvPgo8cmVjdCB4PSIyNi42OSIgeT0iNDQuMSIgc3R5bGU9ImZpbGw6"
    "IzJGNzg4OTsiIHdpZHRoPSI1LjYyIiBoZWlnaHQ9IjE3Ljc5Ii8+CjxwYXRoIHN0eWxlPSJmaWxs"
    "OiMyRjc4ODk7IiBkPSJNMjQuNDgsNjcuODNjMC4xNywxLjM4LDAuNCwzLjUyLDAuNDcsNS43OWMw"
    "LjAyLDAuNzUsMC42MywxLjM0LDEuMzgsMS4zNGgxMC44NAoJYzAuNzgsMCwxLjQxLTAuNjUsMS4z"
    "OS0xLjQzYy0wLjA3LTMuMjYtMC4xNC01LjE2LTAuNC02LjJjLTAuMTYtMC42Mi0wLjcxLTEuMDYt"
    "MS4zNS0xLjA2SDI1Ljg1CglDMjUuMDIsNjYuMjgsMjQuMzcsNjcuMDEsMjQuNDgsNjcuODN6Ii8+"
    "CjxwYXRoIHN0eWxlPSJmaWxsOiM0Q0E4NTQ7IiBkPSJNNDEuNjEsNjcuODNjMC4xMywxLjM4LDAu"
    "MywzLjUyLDAuMzYsNS43OWMwLjAyLDAuNzUsMC40OSwxLjM0LDEuMDYsMS4zNGg4LjMyCgljMC42"
    "LDAsMS4wOC0wLjY1LDEuMDctMS40M2MtMC4wNi0zLjI2LTAuMy01LjE2LTAuNS02LjJjLTAuMTIt"
    "MC42Mi0wLjU0LTEuMDYtMS4wMy0xLjA2aC04LjIyQzQyLjAzLDY2LjI4LDQxLjUzLDY3LjAxLDQx"
    "LjYxLDY3LjgzCgl6Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiM0Q0E4NTQ7IiBkPSJNNTcuMDEsNjcu"
    "ODNjMC4xMywxLjM4LDAuMywzLjUyLDAuMzYsNS43OWMwLjAyLDAuNzUsMC40OSwxLjM0LDEuMDYs"
    "MS4zNGg4LjMyCgljMC42LDAsMS4wOC0wLjY1LDEuMDctMS40M2MtMC4wNi0zLjI2LTAuMy01LjE2"
    "LTAuNS02LjJjLTAuMTItMC42Mi0wLjU0LTEuMDYtMS4wMy0xLjA2aC04LjIyQzU3LjQzLDY2LjI4"
    "LDU2LjkzLDY3LjAxLDU3LjAxLDY3LjgzCgl6Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiNGNDQzMzY7"
    "IiBkPSJNODAuNjIsNDQuMDdWNzYuOWMwLDAuOTcsMC43OSwxLjc2LDEuNzcsMS43NmgzNS42OGMw"
    "Ljk3LDAsMS43Ni0wLjc5LDEuNzYtMS43NlY0NC4wNwoJYzAtMC45Ny0wLjc5LTEuNzYtMS43Ni0x"
    "Ljc2SDgyLjM4QzgxLjQxLDQyLjMxLDgwLjYyLDQzLjEsODAuNjIsNDQuMDd6IE0xMDguMTksNjku"
    "NTRjMCwwLjUyLTAuNDcsMC45NC0xLjA2LDAuOTRIOTMuMzEKCWMtMC41OCwwLTEuMDYtMC40Mi0x"
    "LjA2LTAuOTRWNTIuNDVjMC42Ni0wLjg4LDMuMS0zLjYxLDcuOTctMy42MWM0Ljg4LDAsNy4zMSwy"
    "LjczLDcuOTcsMy42MVY2OS41NHoiLz4KPGc+Cgk8cG9seWdvbiBzdHlsZT0iZmlsbDojNDI0MjQy"
    "OyIgcG9pbnRzPSIxOS4yNiwxMDQuNzEgMTguMTksMTA0LjcxIDguNjYsMTIxLjA4IDEwLjk2LDEy"
    "MS4wOCAJIi8+Cgk8cG9seWdvbiBzdHlsZT0iZmlsbDojNDI0MjQyOyIgcG9pbnRzPSIyMS42Mywx"
    "MDQuNjggMjAuNTgsMTA0LjY4IDE0Ljk5LDEyMS4wOCAxNy4xMywxMjEuMDggCSIvPgo8L2c+Cjxn"
    "PgoJPHBhdGggc3R5bGU9ImZpbGw6I0UyQTYxMDsiIGQ9Ik01Ni4xMyw3NS45NmMwLTcuMTktMS4w"
    "OC0xNC4wNy0xLjA4LTE0LjA3aC0yLjA0YzAsMCwxLjExLDYuMTcsMS4xMSwxNC4wNwoJCWMwLDcu"
    "OTctMC45MiwxMy41Mi0wLjkyLDEzLjUyaDIuMDFDNTUuMjEsODkuNDgsNTYuMTMsODMuNDksNTYu"
    "MTMsNzUuOTZ6Ii8+CjwvZz4KPGc+Cgk8cGF0aCBzdHlsZT0iZmlsbDojRTJBNjEwOyIgZD0iTTcw"
    "Ljk0LDc1Ljk2YzAtNy4xOS0xLjA4LTE0LjA3LTEuMDgtMTQuMDdoLTIuMDRjMCwwLDEuMTEsNi4x"
    "NywxLjExLDE0LjA3CgkJYzAsNy45Ny0wLjg4LDEzLjUyLTAuODgsMTMuNTJoMi4wMUM3MC4wNSw4"
    "OS40OCw3MC45NCw4My40OSw3MC45NCw3NS45NnoiLz4KPC9nPgo8Zz4KCTxwYXRoIHN0eWxlPSJm"
    "aWxsOiM1NDZFN0E7IiBkPSJNMTA3LjU3LDk4LjRMMTA3LjU3LDk4LjRjNC44MiwwLDkuMTEsMy4w"
    "NiwxMC42OCw3LjYyYzAuOTgsMi44NSwwLjgsNS45Mi0wLjUyLDguNjMKCQljLTEuMzIsMi43MS0z"
    "LjYyLDQuNzUtNi40Nyw1Ljc0Yy0xLjIsMC40MS0yLjQ0LDAuNjItMy42OSwwLjYyYy00LjgyLDAt"
    "OS4xMS0zLjA2LTEwLjY4LTcuNjJjLTAuOTgtMi44NS0wLjgtNS45MiwwLjUyLTguNjMKCQljMS4z"
    "Mi0yLjcxLDMuNjItNC43NSw2LjQ3LTUuNzRDMTA1LjA4LDk4LjYsMTA2LjMyLDk4LjQsMTA3LjU3"
    "LDk4LjQgTTEwNy41Nyw5NS40Yy0xLjU1LDAtMy4xMiwwLjI1LTQuNjcsMC43OQoJCWMtNy40Niwy"
    "LjU4LTExLjQzLDEwLjcyLTguODUsMTguMThjMi4wNCw1LjkyLDcuNTksOS42NCwxMy41Miw5LjY0"
    "YzEuNTUsMCwzLjEyLTAuMjUsNC42Ny0wLjc5YzcuNDYtMi41OCwxMS40My0xMC43Miw4Ljg1LTE4"
    "LjE4CgkJQzExOS4wNCw5OS4xMSwxMTMuNSw5NS40LDEwNy41Nyw5NS40TDEwNy41Nyw5NS40eiIv"
    "Pgo8L2c+CjxnPgoJPHBhdGggc3R5bGU9ImZpbGw6I0Y0NDMzNjsiIGQ9Ik0xMDcuNTcsMTAwLjE5"
    "TDEwNy41NywxMDAuMTljNC4wNSwwLDcuNjYsMi41OCw4Ljk5LDYuNDFjMC44MywyLjQsMC42Nyw0"
    "Ljk4LTAuNDQsNy4yNgoJCWMtMS4xMSwyLjI4LTMuMDUsNC01LjQ1LDQuODNjLTEuMDEsMC4zNS0y"
    "LjA1LDAuNTItMy4xLDAuNTJjLTQuMDUsMC03LjY2LTIuNTgtOC45OS02LjQxYy0wLjgzLTIuNC0w"
    "LjY3LTQuOTgsMC40NC03LjI2CgkJYzEuMTEtMi4yOCwzLjA1LTQsNS40NS00LjgzQzEwNS40Nywx"
    "MDAuMzYsMTA2LjUyLDEwMC4xOSwxMDcuNTcsMTAwLjE5IE0xMDcuNTcsOTguMTljLTEuMjUsMC0y"
    "LjUxLDAuMi0zLjc2LDAuNjMKCQljLTYuMDEsMi4wNy05LjIsOC42Mi03LjEyLDE0LjYzYzEuNjQs"
    "NC43Niw2LjEsNy43NiwxMC44OCw3Ljc2YzEuMjUsMCwyLjUxLTAuMiwzLjc2LTAuNjNjNi4wMS0y"
    "LjA3LDkuMi04LjYyLDcuMTItMTQuNjMKCQlDMTE2LjgsMTAxLjE4LDExMi4zNCw5OC4xOSwxMDcu"
    "NTcsOTguMTlMMTA3LjU3LDk4LjE5eiIvPgo8L2c+CjxnPgoJPGxpbmUgc3R5bGU9ImZpbGw6bm9u"
    "ZTtzdHJva2U6I0Y0NDMzNjtzdHJva2Utd2lkdGg6MztzdHJva2UtbWl0ZXJsaW1pdDoxMDsiIHgx"
    "PSIxMTcuNjUiIHkxPSIxMDkuNyIgeDI9Ijk3LjQ4IiB5Mj0iMTA5LjciLz4KCTxsaW5lIHN0eWxl"
    "PSJmaWxsOm5vbmU7c3Ryb2tlOiNGNDQzMzY7c3Ryb2tlLXdpZHRoOjM7c3Ryb2tlLW1pdGVybGlt"
    "aXQ6MTA7IiB4MT0iMTAyLjUyIiB5MT0iMTAwLjk2IiB4Mj0iMTEyLjYxIiB5Mj0iMTE4LjQzIi8+"
    "Cgk8bGluZSBzdHlsZT0iZmlsbDpub25lO3N0cm9rZTojRjQ0MzM2O3N0cm9rZS13aWR0aDozO3N0"
    "cm9rZS1taXRlcmxpbWl0OjEwOyIgeDE9IjEwMi41MiIgeTE9IjExOC40MyIgeDI9IjExMi42MSIg"
    "eTI9IjEwMC45NiIvPgo8L2c+CjxnPgoJPHBhdGggc3R5bGU9ImZpbGw6IzU0NkU3QTsiIGQ9Ik03"
    "Ni40OCw5OC40TDc2LjQ4LDk4LjRjNC44MiwwLDkuMTEsMy4wNiwxMC42OCw3LjYyYzAuOTgsMi44"
    "NSwwLjgsNS45Mi0wLjUyLDguNjMKCQljLTEuMzIsMi43MS0zLjYyLDQuNzUtNi40Nyw1Ljc0Yy0x"
    "LjIsMC40MS0yLjQ0LDAuNjItMy42OSwwLjYyYy00LjgyLDAtOS4xMS0zLjA2LTEwLjY4LTcuNjJj"
    "LTAuOTgtMi44NS0wLjgtNS45MiwwLjUyLTguNjMKCQljMS4zMi0yLjcxLDMuNjItNC43NSw2LjQ3"
    "LTUuNzRDNzMuOTksOTguNiw3NS4yMyw5OC40LDc2LjQ4LDk4LjQgTTc2LjQ4LDk1LjRjLTEuNTUs"
    "MC0zLjEyLDAuMjUtNC42NywwLjc5CgkJYy03LjQ2LDIuNTgtMTEuNDMsMTAuNzItOC44NSwxOC4x"
    "OGMyLjA0LDUuOTIsNy41OSw5LjY0LDEzLjUyLDkuNjRjMS41NSwwLDMuMTItMC4yNSw0LjY3LTAu"
    "NzljNy40Ni0yLjU4LDExLjQzLTEwLjcyLDguODUtMTguMTgKCQlDODcuOTYsOTkuMTEsODIuNDEs"
    "OTUuNCw3Ni40OCw5NS40TDc2LjQ4LDk1LjR6Ii8+CjwvZz4KPGc+Cgk8cGF0aCBzdHlsZT0iZmls"
    "bDojRjQ0MzM2OyIgZD0iTTc2LjQ4LDEwMC4xOUw3Ni40OCwxMDAuMTljNC4wNSwwLDcuNjYsMi41"
    "OCw4Ljk5LDYuNDFjMC44MywyLjQsMC42Nyw0Ljk4LTAuNDQsNy4yNgoJCWMtMS4xMSwyLjI4LTMu"
    "MDUsNC01LjQ1LDQuODNjLTEuMDEsMC4zNS0yLjA1LDAuNTItMy4xLDAuNTJjLTQuMDUsMC03LjY2"
    "LTIuNTgtOC45OS02LjQxYy0wLjgzLTIuNC0wLjY3LTQuOTgsMC40NC03LjI2CgkJYzEuMTEtMi4y"
    "OCwzLjA1LTQsNS40NS00LjgzQzc0LjM5LDEwMC4zNiw3NS40MywxMDAuMTksNzYuNDgsMTAwLjE5"
    "IE03Ni40OCw5OC4xOWMtMS4yNSwwLTIuNTEsMC4yLTMuNzYsMC42MwoJCWMtNi4wMSwyLjA3LTku"
    "Miw4LjYyLTcuMTIsMTQuNjNjMS42NCw0Ljc2LDYuMSw3Ljc2LDEwLjg4LDcuNzZjMS4yNSwwLDIu"
    "NTEtMC4yLDMuNzYtMC42M2M2LjAxLTIuMDcsOS4yLTguNjIsNy4xMi0xNC42MwoJCUM4NS43Miwx"
    "MDEuMTgsODEuMjYsOTguMTksNzYuNDgsOTguMTlMNzYuNDgsOTguMTl6Ii8+CjwvZz4KPGc+Cgk8"
    "bGluZSBzdHlsZT0iZmlsbDpub25lO3N0cm9rZTojRjQ0MzM2O3N0cm9rZS13aWR0aDozO3N0cm9r"
    "ZS1taXRlcmxpbWl0OjEwOyIgeDE9Ijg2LjU3IiB5MT0iMTA5LjciIHgyPSI2Ni40IiB5Mj0iMTA5"
    "LjciLz4KCTxsaW5lIHN0eWxlPSJmaWxsOm5vbmU7c3Ryb2tlOiNGNDQzMzY7c3Ryb2tlLXdpZHRo"
    "OjM7c3Ryb2tlLW1pdGVybGltaXQ6MTA7IiB4MT0iNzEuNDQiIHkxPSIxMDAuOTYiIHgyPSI4MS41"
    "MyIgeTI9IjExOC40MyIvPgoJPGxpbmUgc3R5bGU9ImZpbGw6bm9uZTtzdHJva2U6I0Y0NDMzNjtz"
    "dHJva2Utd2lkdGg6MztzdHJva2UtbWl0ZXJsaW1pdDoxMDsiIHgxPSI3MS40NCIgeTE9IjExOC40"
    "MyIgeDI9IjgxLjUzIiB5Mj0iMTAwLjk2Ii8+CjwvZz4KPHBhdGggc3R5bGU9ImZpbGw6I0UyQTYx"
    "MDsiIGQ9Ik0xMTkuNTgsODkuNTZIODAuNmMtMS40NSwwLTIuNjMtMS4xOC0yLjYzLTIuNjN2LTMu"
    "MzFoNDQuMjN2My4zMQoJQzEyMi4yMSw4OC4zOCwxMjEuMDMsODkuNTYsMTE5LjU4LDg5LjU2eiIv"
    "Pgo8bGluZSBzdHlsZT0iZmlsbDpub25lO3N0cm9rZTojRkZDQTI4O3N0cm9rZS13aWR0aDozO3N0"
    "cm9rZS1saW5lY2FwOnJvdW5kO3N0cm9rZS1taXRlcmxpbWl0OjEwOyIgeDE9Ijc3Ljk3IiB5MT0i"
    "ODIuNjIiIHgyPSIxMjIuMjEiIHkyPSI4Mi42MiIvPgo8bGluZSBzdHlsZT0iZmlsbDpub25lO3N0"
    "cm9rZTojRTJBNjEwO3N0cm9rZS13aWR0aDozO3N0cm9rZS1saW5lY2FwOnJvdW5kO3N0cm9rZS1t"
    "aXRlcmxpbWl0OjEwOyIgeDE9IjU2LjEyIiB5MT0iOTguNDUiIHgyPSIzNC4xNyIgeTI9Ijk4LjQ1"
    "Ii8+CjxnPgoJPHBvbHlsaW5lIHN0eWxlPSJmaWxsOm5vbmU7c3Ryb2tlOiNFMkE2MTA7c3Ryb2tl"
    "LXdpZHRoOjM7c3Ryb2tlLWxpbmVjYXA6cm91bmQ7c3Ryb2tlLW1pdGVybGltaXQ6MTA7IiBwb2lu"
    "dHM9IjExMS4xNCwxMDkuNyAKCQk4MC45OCwxMDkuNyA1My4zLDk3LjU3IAkiLz4KPC9nPgo8cGF0"
    "aCBzdHlsZT0iZmlsbDojNjE2MTYxOyIgZD0iTTIyLjYxLDYxLjljMCwwLTIuODYsNC4yMi0yLjg2"
    "LDEzLjgzczIuOTUsMTMuNzUsMi45NSwxMy43NXMwLjgxLTIuNSwwLjgxLTEyLjMKCVMyMi42MSw2"
    "MS45LDIyLjYxLDYxLjl6Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiM0MjQyNDI7IiBkPSJNMTcuNDcs"
    "NzMuMjVoMi45N2MwLDAsMC4zOCwwLjI1LDAuMzgsMi40NHMtMC4zOCwyLjQ0LTAuMzgsMi40NGgt"
    "Mi45N1Y3My4yNXoiLz4KPHBhdGggc3R5bGU9ImZpbGw6Izc1NzU3NTsiIGQ9Ik0xOC43Myw3NS42"
    "OWMwLDIuMzksMC4wMSw0LjMzLTAuNjcsNC4zM2MtMC42OCwwLTEuNzktMS45NC0xLjc5LTQuMzNz"
    "MS4xMS00LjMzLDEuNzktNC4zMwoJQzE4Ljc0LDcxLjM2LDE4LjczLDczLjMsMTguNzMsNzUuNjl6"
    "Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOiMyMTIxMjE7IiBkPSJNMjMuMTQsODYuMThjLTAuMjIsMi4w"
    "NS0wLjQ1LDMuMy0wLjQ1LDMuM2wxNi42MSwwLjAxYzAsMCwwLjE3LTEuMDYsMC4zMi0zLjE0Cglj"
    "MC4xMS0xLjQ3LTEuMDYtMi43Mi0yLjU0LTIuNzJoLTExLjFDMjQuNTIsODMuNjIsMjMuMjksODQu"
    "NzIsMjMuMTQsODYuMTh6Ii8+CjxyZWN0IHg9IjMzLjEzIiB5PSI5Mi4zNiIgc3R5bGU9ImZpbGw6"
    "IzYwNjA2MDsiIHdpZHRoPSIxNS4zNSIgaGVpZ2h0PSIxMy4yMiIvPgo8ZWxsaXBzZSBzdHlsZT0i"
    "ZmlsbDojNjA2MDYwOyIgY3g9IjQ4LjQ4IiBjeT0iOTguOTciIHJ4PSIxLjU1IiByeT0iNi42MSIv"
    "Pgo8ZWxsaXBzZSBzdHlsZT0iZmlsbDojNjA2MDYwOyIgY3g9IjMzLjEzIiBjeT0iOTguOTciIHJ4"
    "PSIxLjU1IiByeT0iNi42MSIvPgo8cGF0aCBzdHlsZT0iZmlsbDojNzg5MDlDOyIgZD0iTTQ3LjYx"
    "LDk2LjU3SDMzLjg4Yy0wLjUyLDAtMC44OC0wLjQ3LTAuNzktMC45OGMwLjE1LTAuODYsMC4zLTEu"
    "NDksMC43OC0xLjg4CgljMC4xMi0wLjEsMC4yOS0wLjEzLDAuNDUtMC4xM2gxMi45MWMwLjIxLDAs"
    "MC40MywwLjA3LDAuNTYsMC4yM2MwLjQ1LDAuNTEsMC42MSwxLjAzLDAuNjIsMS44MwoJQzQ4LjQx"
    "LDk2LjE5LDQ4LjExLDk2LjU3LDQ3LjYxLDk2LjU3eiIvPgo8cG9seWdvbiBzdHlsZT0iZmlsbDoj"
    "MDA0RDQwOyIgcG9pbnRzPSIxMjIuMiw0MC40NSA3Ny45OSw0MC40NSA3NS4xNSwzOC45NCAxMjUu"
    "MDQsMzguOTQgIi8+CjxyZWN0IHg9Ijc1LjE1IiB5PSIzNS4xOCIgc3R5bGU9ImZpbGw6IzAwNzk2"
    "QjsiIHdpZHRoPSI0OS44OSIgaGVpZ2h0PSIzLjc2Ii8+CjxwYXRoIHN0eWxlPSJmaWxsOm5vbmU7"
    "c3Ryb2tlOiNDNjI4Mjg7c3Ryb2tlLXdpZHRoOjI7c3Ryb2tlLW1pdGVybGltaXQ6MTA7IiBkPSJN"
    "MTA4LjE5LDY5LjU0YzAsMC41Mi0wLjQ3LDAuOTQtMS4wNiwwLjk0SDkzLjMxCgljLTAuNTgsMC0x"
    "LjA2LTAuNDItMS4wNi0wLjk0VjUyLjQ1YzAuNjYtMC44OCwzLjEtMy42MSw3Ljk3LTMuNjFjNC44"
    "OCwwLDcuMzEsMi43Myw3Ljk3LDMuNjFWNjkuNTR6Ii8+Cjwvc3ZnPgo="
)

# heading → pygame.transform.rotate angle (sprite points right = East)
_HEADING_ROT = {
    'E':  0, 'NE': 45, 'N':  90, 'NW': 135,
    'W': 180, 'SW': 225, 'S': 270, 'SE': 315,
}
# heading → (dx, dy) unit vector (used for motion trail offset)
_HEADING_VEC = {
    'N':  (0, -1),  'NE': ( 0.707, -0.707), 'E':  (1, 0),   'SE': ( 0.707, 0.707),
    'S':  (0,  1),  'SW': (-0.707,  0.707), 'W': (-1, 0),   'NW': (-0.707, -0.707),
}

# Cached base sprite (raw Noto, no tint) — loaded once
_BASE_SPRITE_CACHE: dict = {}   # size → pygame.Surface


def _load_base_sprite(size: int = 48) -> pygame.Surface:
    """
    Decode the embedded SVG and render it via rsvg-convert to a pygame SRCALPHA surface.
    Falls back to a simple colored rectangle if rsvg-convert is unavailable.
    Cached per size so it only runs once.
    """
    if size in _BASE_SPRITE_CACHE:
        return _BASE_SPRITE_CACHE[size]

    surf = None
    try:
        import subprocess, tempfile, os
        svg_bytes = base64.b64decode(_TRAIN_SVG_B64)
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
            f.write(svg_bytes)
            svg_path = f.name
        png_path = svg_path.replace('.svg', '.png')
        result = subprocess.run(
            ['rsvg-convert', '-w', str(size), '-h', str(size), svg_path, '-o', png_path],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            pil_img = Image.open(png_path).convert('RGBA')
            mode = pil_img.mode
            raw  = pil_img.tobytes()
            surf = pygame.image.fromstring(raw, pil_img.size, mode).convert_alpha()
        os.unlink(svg_path)
        if os.path.exists(png_path):
            os.unlink(png_path)
    except Exception:
        pass

    if surf is None:
        # Fallback: simple locomotive silhouette drawn with pygame
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        body_h = int(size * 0.45)
        oy = (size - body_h) // 2
        pygame.draw.rect(surf, (80, 80, 90), (4, oy, size - 8, body_h), border_radius=6)
        pygame.draw.rect(surf, (60, 60, 70), (size - 14, oy - 4, 12, body_h + 8), border_radius=4)
        pygame.draw.circle(surf, (200, 200, 210), (size - 7, oy + body_h // 2), 4)

    _BASE_SPRITE_CACHE[size] = surf
    return surf


def _make_train_sprite(color: tuple, size: int = 48) -> pygame.Surface:
    """
    Return a tinted copy of the Noto train sprite.
    The original Noto colors are preserved but overlaid with a soft color wash
    so each route's trains have a recognizable accent color.
    """
    base = _load_base_sprite(size)
    tinted = base.copy()

    r, g, b = color
    # Create a semi-transparent color wash surface and blend it over the sprite
    wash = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    wash.fill((r, g, b, 55))   # 55/255 ≈ 22% tint — subtle, preserves detail
    tinted.blit(wash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return tinted


class MapRenderer:
    """Renders the tiled map with railway overlay and train/station markers."""

    def __init__(self, tile_cache: TileCache, width: int, height: int):
        self.tile_cache = tile_cache
        self.width = width
        self.height = height
        self.zoom = TILE_ZOOM

        # fractional tile position of the origin lat/lon
        lat_r = math.radians(ORIGIN_LAT)
        n = 2 ** self.zoom
        self._origin_ftx = (ORIGIN_LON + 180.0) / 360.0 * n
        self._origin_fty = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n

        # pixel on the surface that corresponds to origin lat/lon (dead center)
        self._cx_px = width / 2.0
        self._cy_px = height / 2.0

        # tile grid that covers the panel
        tiles_x = math.ceil(width / TILE_SIZE) + 2
        tiles_y = math.ceil(height / TILE_SIZE) + 2

        # top-left tile index
        self.origin_tile_x = int(self._origin_ftx) - tiles_x // 2
        self.origin_tile_y = int(self._origin_fty) - tiles_y // 2
        self.tiles_x = tiles_x + 2
        self.tiles_y = tiles_y + 2

        # kick off prefetch of basemap tiles only
        tile_cache.prefetch(
            OSM_TILE_URL, self.zoom,
            range(self.origin_tile_x, self.origin_tile_x + self.tiles_x),
            range(self.origin_tile_y, self.origin_tile_y + self.tiles_y),
        )

        self._surface = pygame.Surface((width, height))

        # sprite/rotation cache: (color_hex, heading) → rotated pygame.Surface
        self._rot_cache: dict = {}
        # label font for train numbers
        self._num_font = pygame.font.Font(None, 18)

    def _latlon_to_px(self, lat, lon):
        """Convert lat/lon to pixel coordinates on the map surface."""
        lat_r = math.radians(lat)
        n = 2 ** self.zoom
        ftx = (lon + 180.0) / 360.0 * n
        fty = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
        px = self._cx_px + (ftx - self._origin_ftx) * TILE_SIZE
        py = self._cy_px + (fty - self._origin_fty) * TILE_SIZE
        return int(px), int(py)

    def _px_to_latlon(self, px: float, py: float):
        """Inverse projection from map-surface pixel to lat/lon."""
        n = 2 ** self.zoom
        ftx = self._origin_ftx + (px - self._cx_px) / TILE_SIZE
        fty = self._origin_fty + (py - self._cy_px) / TILE_SIZE
        lon = ftx / n * 360.0 - 180.0
        lat_r = math.atan(math.sinh(math.pi * (1.0 - 2.0 * fty / n)))
        lat = math.degrees(lat_r)
        return lat, lon

    def get_view_bbox(self, pad_px: int = 0):
        """Return visible map bbox as (min_lat, min_lon, max_lat, max_lon)."""
        corners = [
            self._px_to_latlon(0 - pad_px, 0 - pad_px),
            self._px_to_latlon(self.width + pad_px, 0 - pad_px),
            self._px_to_latlon(0 - pad_px, self.height + pad_px),
            self._px_to_latlon(self.width + pad_px, self.height + pad_px),
        ]
        lats = [c[0] for c in corners]
        lons = [c[1] for c in corners]
        return (min(lats), min(lons), max(lats), max(lons))

    def render(self, surface: pygame.Surface, infrastructure: dict, trains: list,
               font_label: pygame.font.Font, font_small: pygame.font.Font,
               dest_xy: tuple[int, int] = (0, 0)):
        """Draw map onto the provided surface."""
        self._surface.fill(C_BG)

        # draw CartoDB light basemap tiles
        for dx in range(self.tiles_x):
            for dy in range(self.tiles_y):
                tx = self.origin_tile_x + dx
                ty = self.origin_tile_y + dy
                tile = self.tile_cache.get(OSM_TILE_URL, self.zoom, tx, ty)
                px = int(self._cx_px + (tx - self._origin_ftx) * TILE_SIZE)
                py = int(self._cy_px + (ty - self._origin_fty) * TILE_SIZE)
                if tile:
                    self._surface.blit(tile, (px, py))
                else:
                    pygame.draw.rect(self._surface, (235, 235, 228),
                                     pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(self._surface, (210, 210, 200),
                                     pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 1)

        # draw Amtrak station markers from known coordinates
        for code, (slat, slon, sname) in AMTRAK_STATION_COORDS.items():
            px, py = self._latlon_to_px(slat, slon)
            if -10 <= px < self.width + 10 and -10 <= py < self.height + 10:
                pygame.draw.circle(self._surface, C_STATION_DOT, (px, py), 5)
                pygame.draw.circle(self._surface, C_TEXT, (px, py), 5, 1)
                lbl = font_small.render(sname, True, C_TEXT)
                self._surface.blit(lbl, (px + 7, py - 6))

        # ── draw live Amtrak train positions ──────────────────────────
        for train in trains:
            tlat = train.get("lat")
            tlon = train.get("lon")
            if not tlat or not tlon:
                continue
            px, py = self._latlon_to_px(tlat, tlon)
            if -80 <= px < self.width + 80 and -80 <= py < self.height + 80:
                num      = str(train.get("trainNum", "?"))
                velocity = float(train.get("velocity") or 0)
                heading  = (train.get("heading") or "E").upper().strip()
                if heading not in _HEADING_ROT:
                    heading = "E"

                dot_color = _parse_hex_color(train.get("iconColor") or "#e8a020", (232, 160, 32))

                # Draw a clean labeled dot instead of the old animated sprite.
                dot_r = 14
                if len(num) >= 4:
                    dot_r = 16
                elif len(num) == 3:
                    dot_r = 15

                # direction indicator: a short arrow pointing along travel heading
                vec = _HEADING_VEC.get(heading, _HEADING_VEC["E"])
                arrow_len = dot_r + 10
                ax0 = int(px + vec[0] * 4)
                ay0 = int(py + vec[1] * 4)
                ax1 = int(px + vec[0] * arrow_len)
                ay1 = int(py + vec[1] * arrow_len)
                try:
                    pygame.draw.line(self._surface, (20, 20, 24), (ax0, ay0), (ax1, ay1), 4)
                    pygame.draw.line(self._surface, (250, 250, 250), (ax0, ay0), (ax1, ay1), 2)
                    head_left = (
                        int(ax1 - vec[0] * 5 - vec[1] * 4),
                        int(ay1 - vec[1] * 5 + vec[0] * 4),
                    )
                    head_right = (
                        int(ax1 - vec[0] * 5 + vec[1] * 4),
                        int(ay1 - vec[1] * 5 - vec[0] * 4),
                    )
                    pygame.draw.polygon(self._surface, (20, 20, 24), [(ax1, ay1), head_left, head_right])
                    pygame.draw.polygon(self._surface, (250, 250, 250), [(ax1, ay1), head_left, head_right], 1)
                except Exception:
                    pass

                # main dot
                pygame.draw.circle(self._surface, (20, 20, 24), (px + 1, py + 1), dot_r + 1)
                pygame.draw.circle(self._surface, dot_color, (px, py), dot_r)
                pygame.draw.circle(self._surface, (255, 255, 255), (px, py), dot_r, 2)

                # train number centered on the dot
                num_font = pygame.font.Font(None, 15 if len(num) >= 3 else 18)
                num_surf = num_font.render(num, True, (255, 255, 255))
                num_dark = num_font.render(num, True, (15, 15, 20))
                tx = px - num_surf.get_width() // 2
                ty = py - num_surf.get_height() // 2
                for odx, ody in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._surface.blit(num_dark, (tx + odx, ty + ody))
                self._surface.blit(num_surf, (tx, ty))

        # draw origin crosshair
        ox, oy = self._latlon_to_px(ORIGIN_LAT, ORIGIN_LON)
        pygame.draw.circle(self._surface, C_ACCENT, (ox, oy), 8, 2)
        pygame.draw.line(self._surface, C_ACCENT, (ox - 14, oy), (ox + 14, oy), 1)
        pygame.draw.line(self._surface, C_ACCENT, (ox, oy - 14), (ox, oy + 14), 1)

        # draw bounding radius ring (dashed-ish)
        d_lat = MAP_RADIUS_MILES / 69.0
        edge_px, _ = self._latlon_to_px(ORIGIN_LAT, ORIGIN_LON + MAP_RADIUS_MILES / (
            69.0 * math.cos(math.radians(ORIGIN_LAT))))
        radius_px = abs(edge_px - ox)
        if radius_px > 10:
            pygame.draw.circle(self._surface, C_PANEL_BORDER, (ox, oy), radius_px, 1)

        surface.blit(self._surface, dest_xy)

# ═══════════════════════════════════════════════════════════════════
# SECTION 8: SCHEDULE PANEL
# ═══════════════════════════════════════════════════════════════════

class SchedulePanel:
    """Displays upcoming Amtrak stops at nearby stations with real times."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self._entries = []       # list of schedule entry dicts from AmtrakerClient
        self._last_update = 0
        self._page_started = time.time()

    def update(self, entries: list):
        """entries from AmtrakerClient.get_nearby_schedule()"""
        self._entries = entries[:]
        self._last_update = time.time()
        self._page_started = time.time()

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font, font_small: pygame.font.Font):
        from datetime import datetime, timezone
        r = self.rect
        pygame.draw.rect(surface, C_PANEL_BG, r)
        pygame.draw.rect(surface, C_PANEL_BORDER, r, 1)

        y = r.top + 10
        now_utc = datetime.now(timezone.utc)

        if self._entries:
            row_h = font_body.get_height() + (font_small.get_height() * 2) + 6
            footer_h = font_small.get_height() + 14
            available_h = max(0, (r.bottom - footer_h) - y)
            rows_per_page = max(1, available_h // row_h)
            total_pages = max(1, math.ceil(len(self._entries) / rows_per_page))
            elapsed = max(0.0, time.time() - self._page_started)
            page_idx = int(elapsed / SCHEDULE_PAGE_ROTATE_SEC) % total_pages
            page_start = page_idx * rows_per_page
            page_entries = self._entries[page_start:page_start + rows_per_page]

            for entry in page_entries:

                num        = str(entry.get("train_num", "?"))
                route      = entry.get("route_name", "")
                stn        = entry.get("station_name", "?")[:16]
                est        = entry.get("est_dep")
                sch        = entry.get("sch_dep")
                status     = entry.get("status", "")
                delay      = entry.get("delay_min", 0)
                dist       = entry.get("dist_miles", 0)
                destination = str(entry.get("destination", "?"))
                next_stop   = str(entry.get("next_stop", "—"))
                direction   = str(entry.get("direction", "?"))
                speed_mph   = float(entry.get("speed_mph") or 0.0)

                # format scheduled time in local tz
                try:
                    local_sch = sch.astimezone()
                    time_str = local_sch.strftime("%H:%M")
                except Exception:
                    time_str = "--:--"

                # color by status/delay
                if status == "Departed":
                    row_color = C_TEXT_DIM
                elif delay > 15:
                    row_color = (255, 100, 80)
                elif delay > 5:
                    row_color = C_ACCENT2
                else:
                    row_color = C_TEXT

                delay_tag = ""
                if delay > 2:
                    delay_tag = f"+{delay}m"
                elif delay < -2:
                    delay_tag = f"{delay}m"

                status_short = (status or "Sched")[:8]
                row_text = f"  #{num:<6} {stn:<18} {time_str:>6}  {status_short:<8} {delay_tag}"
                row = font_body.render(row_text[:52], True, row_color)
                surface.blit(row, (r.left, y))
                y += row.get_height()

                # sub-line 1: route + destination + nearest-station distance
                sub = font_small.render(
                    f"    {route[:16]}  to {destination[:16]}  ({dist:.0f} mi)",
                    True, C_TEXT_DIM
                )
                surface.blit(sub, (r.left, y))
                y += sub.get_height() + 1

                # sub-line 2: next stop + ETA + direction/speed
                try:
                    mins = int((est - now_utc).total_seconds() / 60)
                    if mins <= 0:
                        eta = "NOW"
                    else:
                        eta = f"{mins}m"
                except Exception:
                    eta = "--"
                sub2 = font_small.render(
                    f"    next: {next_stop[:16]}  ETA {eta:<4}  {direction:>2} {speed_mph:.0f} mph",
                    True, C_TEXT_DIM
                )
                surface.blit(sub2, (r.left, y))
                y += sub2.get_height() + 4

            if total_pages > 1:
                page_label = font_small.render(
                    f"Page {page_idx + 1}/{total_pages}", True, C_TEXT_DIM
                )
                surface.blit(page_label, (r.right - page_label.get_width() - 8, r.bottom - page_label.get_height() - 6))

                frac = (elapsed % SCHEDULE_PAGE_ROTATE_SEC) / SCHEDULE_PAGE_ROTATE_SEC
                bar_w = int((r.width - 20) * (1.0 - frac))
                if bar_w > 0:
                    pygame.draw.rect(surface, C_ACCENT,
                                     pygame.Rect(r.left + 10, r.bottom - 6, bar_w, 3))

        else:
            msg = font_body.render("  Fetching schedule data…", True, C_TEXT_DIM)
            surface.blit(msg, (r.left + 8, y))

        # last update footer
        if self._last_update:
            ts = time.strftime("%H:%M:%S", time.localtime(self._last_update))
            upd = font_small.render(f"Updated {ts}", True, C_TEXT_DIM)
            surface.blit(upd, (r.left + 8, r.bottom - upd.get_height() - 4))

# ═══════════════════════════════════════════════════════════════════
# SECTION 9: UPCOMING WATCH PANEL
# ═══════════════════════════════════════════════════════════════════

class UpcomingWatchPanel:
    """Shows the best nearby trains to watch, with ETA and distance."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self._items = []   # top entries from schedule

    def update(self, schedule_entries: list):
        """
        Pick the best 5 trains to watch: those with upcoming (non-departed)
        stops at the closest stations, sorted by how soon they arrive.
        """
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)

        candidates = []
        for e in schedule_entries:
            status = e.get("status", "")
            if status == "Departed":
                continue
            est = e.get("est_dep")
            if not est:
                continue
            minutes_away = (est - now_utc).total_seconds() / 60
            if minutes_away < -5:  # already left
                continue
            dist = e.get("dist_miles", 9999)
            # score: closer station + sooner = better
            score = dist + max(0, minutes_away) * 0.5
            candidates.append((score, e))

        candidates.sort(key=lambda x: x[0])
        self._items = [e for _, e in candidates[:5]]

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font, font_small: pygame.font.Font):
        from datetime import datetime, timezone
        r = self.rect
        pygame.draw.rect(surface, C_PANEL_BG, r)
        pygame.draw.rect(surface, C_PANEL_BORDER, r, 1)

        y = r.top + 8
        title = font_title.render("◈ BEST TRAINS TO WATCH", True, C_ACCENT)
        surface.blit(title, (r.left + 10, y))
        y += title.get_height() + 4
        pygame.draw.line(surface, C_SEPARATOR, (r.left + 8, y), (r.right - 8, y), 1)
        y += 6

        now_utc = datetime.now(timezone.utc)

        if self._items:
            for i, entry in enumerate(self._items):
                if y + font_body.get_height() + 2 > r.bottom - 4:
                    break

                num   = str(entry.get("train_num", "?"))
                route = entry.get("route_name", "")
                stn   = entry.get("station_name", "?")
                dist  = entry.get("dist_miles", 0)
                est   = entry.get("est_dep")
                delay = entry.get("delay_min", 0)

                icon  = "★" if i == 0 else "◆"
                color = C_ACCENT2 if i == 0 else C_TEXT

                try:
                    mins = int((est - now_utc).total_seconds() / 60)
                    local_t = est.astimezone().strftime("%H:%M")
                    if mins <= 0:
                        eta_str = f"NOW  @{local_t}"
                    elif mins < 60:
                        eta_str = f"~{mins}m  @{local_t}"
                    else:
                        eta_str = f"~{mins//60}h{mins%60:02d}m  @{local_t}"
                except Exception:
                    eta_str = "--"

                delay_tag = f"  (+{delay}m)" if delay > 2 else ("  (early)" if delay < -2 else "")
                row = font_body.render(
                    f"  {icon} #{num}  {route[:22]}", True, color)
                surface.blit(row, (r.left, y))
                y += row.get_height()

                sub = font_small.render(
                    f"    {stn[:20]}  {dist:.0f}mi  {eta_str}{delay_tag}",
                    True, C_TEXT_DIM)
                surface.blit(sub, (r.left, y))
                y += sub.get_height() + 5
        else:
            msg = font_small.render("  No upcoming trains nearby", True, C_TEXT_DIM)
            surface.blit(msg, (r.left + 4, y))

# ═══════════════════════════════════════════════════════════════════
# SECTION 10: MOTD PANEL
# ═══════════════════════════════════════════════════════════════════

class MotdPanel:
    """Cycles through train facts randomly every MOTD_ROTATE_SEC seconds."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self._facts = MOTD_FACTS[:]
        random.shuffle(self._facts)
        self._index = 0
        self._last_rotate = time.time()
        self._current = self._facts[0]

    def update(self):
        if time.time() - self._last_rotate >= MOTD_ROTATE_SEC:
            self._index = (self._index + 1) % len(self._facts)
            if self._index == 0:
                random.shuffle(self._facts)
            self._current = self._facts[self._index]
            self._last_rotate = time.time()

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font):
        r = self.rect
        pygame.draw.rect(surface, C_MOTD_BG, r)
        pygame.draw.rect(surface, C_MOTD_BORDER, r, 2)

        y = r.top + 8
        title = font_title.render("◈ TRAIN FACT", True, C_ACCENT)
        surface.blit(title, (r.left + 10, y))
        y += title.get_height() + 6

        # word-wrap the fact into the panel width
        words = self._current.split()
        lines = []
        line = ""
        max_w = r.width - 24
        for word in words:
            test = (line + " " + word).strip()
            w, _ = font_body.size(test)
            if w <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        for ln in lines:
            if y + font_body.get_height() > r.bottom - 8:
                break
            lbl = font_body.render(ln, True, C_TEXT)
            surface.blit(lbl, (r.left + 12, y))
            y += font_body.get_height() + 2

        # countdown bar
        elapsed = time.time() - self._last_rotate
        frac = min(1.0, elapsed / MOTD_ROTATE_SEC)
        bar_w = int((r.width - 20) * (1.0 - frac))
        if bar_w > 0:
            pygame.draw.rect(surface, C_ACCENT,
                             pygame.Rect(r.left + 10, r.bottom - 6, bar_w, 3))

# ═══════════════════════════════════════════════════════════════════
# SECTION 11: MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

class TrainStationApp:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Train Station")

        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        try:
            self.screen = pygame.display.set_mode((0, 0), flags)
        except Exception:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.screen_w, self.screen_h = self.screen.get_size()

        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        # fonts
        self._init_fonts()

        # layout rects
        content_w = self.screen_w - (PANEL_GAP * 2)
        map_w = int((content_w - PANEL_GAP) * 0.70)
        right_x = PANEL_GAP + map_w + PANEL_GAP
        right_w = content_w - map_w - PANEL_GAP

        self.map_rect = pygame.Rect(PANEL_GAP, PANEL_GAP, map_w, self.screen_h - (PANEL_GAP * 2))
        header_h = 60
        self.header_rect = pygame.Rect(right_x, PANEL_GAP, right_w, header_h)

        side_content_h = self.screen_h - self.header_rect.bottom - (PANEL_GAP * 2)
        schedule_h = side_content_h

        self.schedule_rect = pygame.Rect(right_x, self.header_rect.bottom + PANEL_GAP, right_w, schedule_h)
        self.motd_rect = pygame.Rect(
            self.map_rect.left + PANEL_GAP,
            self.screen_h - PANEL_GAP - BOTTOM_PANEL_H,
            self.map_rect.width - (PANEL_GAP * 2),
            BOTTOM_PANEL_H
        )

        # subsystems
        self.tile_cache = TileCache()
        self.amtraker = AmtrakerClient()
        self.map_renderer = MapRenderer(self.tile_cache, self.map_rect.width, self.map_rect.height)
        self.schedule_panel = SchedulePanel(self.schedule_rect)
        self.motd_panel = MotdPanel(self.motd_rect)

        # data state
        self._amtrak_trains = []   # live train positions for map
        self._bbox = self.map_renderer.get_view_bbox(pad_px=120)
        self._last_data_update = 0
        self._data_lock = threading.Lock()

        # kick off first data fetch in background
        self._schedule_data_update()

    def _init_fonts(self):
        """Load fonts, falling back to pygame default."""
        # try to find a system monospace / sans font
        candidates = [
            "dejavusansmono", "liberationmono", "freemono",
            "ubuntumono", "couriernew", "courier",
            "dejavusans", "liberationsans", "freesans", "ubuntu",
        ]
        body_font = None
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, 18)
                if f:
                    body_font = name
                    break
            except Exception:
                pass

        self.font_title = pygame.font.SysFont(body_font, 20, bold=True) if body_font else pygame.font.Font(None, 22)
        self.font_body = pygame.font.SysFont(body_font, 18) if body_font else pygame.font.Font(None, 20)
        self.font_fact = pygame.font.SysFont(body_font, 21) if body_font else pygame.font.Font(None, 24)
        self.font_small = pygame.font.SysFont(body_font, 15) if body_font else pygame.font.Font(None, 17)
        self.font_clock = pygame.font.SysFont(body_font, 32, bold=True) if body_font else pygame.font.Font(None, 36)

    def _fetch_data(self):
        """Fetch Amtrak data for map + information panel."""
        amtrak_trains = [None]
        amtrak_sched  = [None]

        def fetch_amtrak():
            amtrak_trains[0] = self.amtraker.get_trains_in_bbox(self._bbox)
            amtrak_sched[0]  = self.amtraker.get_nearby_schedule(MAP_RADIUS_MILES)

        t_amtrak = threading.Thread(target=fetch_amtrak, daemon=True)
        t_amtrak.start()

        # Amtrak is fast (~1s); update map immediately when it returns
        t_amtrak.join(timeout=25)
        if amtrak_trains[0] is not None:
            with self._data_lock:
                self._amtrak_trains = amtrak_trains[0]
                self._last_data_update = time.time()
            if amtrak_sched[0]:
                self.schedule_panel.update(amtrak_sched[0])

    def _schedule_data_update(self):
        t = threading.Thread(target=self._fetch_data, daemon=True)
        t.start()

    def _render_header(self):
        r = self.header_rect
        pygame.draw.rect(self.screen, C_HEADER_BG, r)
        pygame.draw.rect(self.screen, C_PANEL_BORDER, r, 1)

        now = time.localtime()
        time_str = time.strftime("%H:%M:%S", now)
        date_str = time.strftime("%A, %B %d %Y", now)

        time_surf = self.font_clock.render(time_str, True, C_ACCENT2)
        date_surf = self.font_small.render(date_str, True, C_TEXT_DIM)

        self.screen.blit(time_surf, (r.left + 12, r.top + 8))
        self.screen.blit(date_surf, (r.left + 12, r.top + 38))

        # location label
        loc = self.font_small.render(f"Frederick, MD  ·  {MAP_RADIUS_MILES} mi radius", True, C_TEXT_DIM)
        self.screen.blit(loc, (r.right - loc.get_width() - 10, r.top + 8))

        # connection status
        if self._last_data_update:
            age = time.time() - self._last_data_update
            if age < 120:
                status = self.font_small.render("● LIVE", True, (80, 255, 100))
            else:
                status = self.font_small.render("● STALE", True, C_ACCENT2)
        else:
            status = self.font_small.render("○ LOADING", True, C_TEXT_DIM)
        self.screen.blit(status, (r.right - status.get_width() - 10, r.top + 26))

    def run(self):
        running = True
        last_update_check = 0

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            now = time.time()

            # schedule periodic data refresh
            if now - last_update_check >= TRAIN_UPDATE_SEC:
                self._schedule_data_update()
                last_update_check = now

            # update MOTD rotation
            self.motd_panel.update()

            # render
            self.screen.fill(C_BG)

            with self._data_lock:
                trains = self._amtrak_trains

            self.map_renderer.render(
                self.screen, {}, trains,
                self.font_body, self.font_small,
                self.map_rect.topleft
            )

            self._render_header()

            self.schedule_panel.render(
                self.screen, self.font_title, self.font_body, self.font_small
            )

            self.motd_panel.render(
                self.screen, self.font_title, self.font_fact
            )

            pygame.display.flip()
            self.clock.tick(FPS_CAP)

        pygame.quit()
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = TrainStationApp()
    app.run()
