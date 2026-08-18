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
FPS_CAP = 20

TRAIN_UPDATE_SEC = 30       # how often to refresh train positions
SCHEDULE_UPDATE_SEC = 30    # how often to refresh schedules
MOTD_ROTATE_SEC = 30        # how often to cycle train fact
SCHEDULE_PAGE_ROTATE_SEC = 10  # how often to flip Train Information pages
PROGRESS_UPDATE_HZ = 20         # animate progress train per second
SELF_UPDATE_INTERVAL_S = 5 * 60
SELF_UPDATE_TIMEOUT_S = 120

MAP_PANEL_W = int(SCREEN_W * 0.70)   # 1344 px
SIDE_PANEL_W = SCREEN_W - MAP_PANEL_W  # 576 px
BOTTOM_PANEL_H = 90
PANEL_GAP = 16

TILE_SIZE = 256             # OSM tile size in pixels
TILE_ZOOM = 9               # zoom level (9 zooms in a bit tighter on the origin area)
OSM_TILE_URL = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
PAGE_TRAIN_GIF_URL = "https://www.animatedimages.org/data/media/75/animated-train-image-0043.gif"

# ── Colors ──────────────────────────────────────────────────────────
C_BG          = (8,  12,  18)
C_PANEL_BG    = (16,  22,  30)
C_PANEL_BORDER= (48,  64,  82)
C_HEADER_BG   = (16,  22,  30)
C_TEXT        = (226, 233, 242)
C_TEXT_DIM    = (144, 159, 176)
C_ACCENT      = (83,  160, 255)
C_ACCENT2     = (255, 174, 70)
C_TRAIN_DOT   = (255, 240,  80)
C_STATION_DOT = (95,  112, 132)
C_TRACK       = (100, 200, 100)
C_SEPARATOR   = (40,  55,  72)
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
import io
import subprocess
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

import base64

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

def _log_http(method: str, url: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] HTTP {method} {url}"
    if detail:
        msg += f" :: {detail}"
    print(msg, flush=True)

def _load_whimsical_train_sprite(target_h: int = 32):
    """Load train GIF and convert white pixels to transparent for UI overlays."""
    try:
        resp = requests.get(PAGE_TRAIN_GIF_URL, timeout=8)
        _log_http("GET", PAGE_TRAIN_GIF_URL, f"status={resp.status_code}")
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        px = img.load()
        w, h = img.size
        for yy in range(h):
            for xx in range(w):
                r, g, b, _ = px[xx, yy]
                if r >= 245 and g >= 245 and b >= 245:
                    px[xx, yy] = (255, 255, 255, 0)
        out_h = max(12, int(target_h))
        out_w = max(20, int(w * (out_h / max(1, h))))
        img = img.resize((out_w, out_h), Image.Resampling.LANCZOS)
        return pygame.image.fromstring(img.tobytes(), img.size, "RGBA").convert_alpha()
    except Exception:
        _log_http("GET", PAGE_TRAIN_GIF_URL, "error")
        return None

def _git_head(repo_dir: str):
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return proc.stdout.strip()
    except Exception as e:
        print(f"Self-update: git rev-parse failed: {e}", flush=True)
        return None

def _maybe_self_update_and_restart(repo_dir: str) -> bool:
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        return False

    before = _git_head(repo_dir)
    print("Self-update: running git pull", flush=True)
    try:
        pull = subprocess.run(
            ["git", "pull"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=SELF_UPDATE_TIMEOUT_S,
        )
    except Exception as e:
        print(f"Self-update: git pull failed: {e}", flush=True)
        return False

    stdout = (pull.stdout or "").strip()
    stderr = (pull.stderr or "").strip()
    if stdout:
        print(f"Self-update git pull stdout: {stdout}", flush=True)
    if stderr:
        print(f"Self-update git pull stderr: {stderr}", flush=True)
    if pull.returncode != 0:
        print(f"Self-update: git pull exited with status {pull.returncode}", flush=True)
        return False

    after = _git_head(repo_dir)
    combined = f"{stdout}\n{stderr}"
    already_up_to_date = (
        "Already up to date." in combined
        or "Already up-to-date." in combined
    )
    if before and after:
        updated = before != after
    else:
        updated = not already_up_to_date

    if not updated:
        print("Self-update: no remote updates found", flush=True)
        return False

    script_path = os.path.abspath(__file__)
    print("Self-update: updates found, launching fresh process", flush=True)
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        subprocess.Popen([sys.executable, "-u", script_path], cwd=repo_dir, env=env)
        return True
    except Exception as e:
        print(f"Self-update: failed to launch fresh process: {e}", flush=True)
        return False

# ═══════════════════════════════════════════════════════════════════
# SECTION 5: TRANSITDOCS CLIENT
# ═══════════════════════════════════════════════════════════════════

class MapTileOverlay:
    """Non-blocking in-memory tile cache for subdued dark basemap overlay."""

    def __init__(self, url_template: str, max_tiles: int = 420):
        self.url_template = url_template
        self.max_tiles = max_tiles
        self._cache: OrderedDict = OrderedDict()
        self._pending = set()
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "TrainStationKiosk/1.0 (train enthusiast display; contact: kiosk@local)"
        })

    def get(self, z: int, x: int, y: int):
        key = (z, x, y)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            if key in self._pending:
                return None
            self._pending.add(key)
        threading.Thread(target=self._fetch_tile, args=(key,), daemon=True).start()
        return None

    def _fetch_tile(self, key):
        z, x, y = key
        url = self.url_template.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
        surf = None
        try:
            resp = self._session.get(url, timeout=8)
            _log_http("GET", url, f"status={resp.status_code}")
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                surf = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
        except Exception:
            _log_http("GET", url, "error")
            surf = None
        finally:
            with self._lock:
                self._pending.discard(key)
                if surf is not None:
                    self._cache[key] = surf
                    self._cache.move_to_end(key)
                    while len(self._cache) > self.max_tiles:
                        self._cache.popitem(last=False)

    def get_stats(self) -> tuple[int, int]:
        """Return (cached_tiles, pending_tiles) for render throttling."""
        with self._lock:
            return len(self._cache), len(self._pending)


class TransitDocsClient:
    """Transitdocs-only data client for trains, stations, schedules, and rail overlay."""

    BASE_URLS = (
        "https://asm.transitdocs.com",
        "https://asm-backend.transitdocs.com",
    )
    CACHE_SEC = 30
    PROVIDER_COLORS = {
        "AMTRAK": "#1f6fe5",
        "VIA": "#e24b4b",
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._cache_ts = 0.0
        self._cache = {
            "trains": [],
            "stations": [],
            "station_by_code": {},
            "tracks": [],
        }
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "TrainStationKiosk/1.0 (train enthusiast display; contact: kiosk@local)",
            "Accept": "application/json",
        })

    def _fetch_json(self, path: str):
        for base in self.BASE_URLS:
            url = f"{base.rstrip('/')}/{path.lstrip('/')}"
            try:
                resp = self._session.get(url, timeout=20)
                _log_http("GET", url, f"status={resp.status_code}")
                if resp.status_code != 200:
                    continue
                content_type = (resp.headers.get("content-type") or "").lower()
                if "json" not in content_type:
                    continue
                return resp.json()
            except (requests.RequestException, json.JSONDecodeError):
                _log_http("GET", url, "error")
                continue
        return None

    def _to_dt(self, ts):
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    def _stop_est_dt(self, stop: dict, prefer: str = "depart") -> "datetime | None":
        """
        Return the estimated datetime for a stop, combining sched timestamp + variance.
        prefer='depart' tries depart first, then arrive; 'arrive' is the reverse.
        """
        if prefer == "depart":
            timing_keys = [("depart", "sched_depart"), ("arrive", "sched_arrive")]
        else:
            timing_keys = [("arrive", "sched_arrive"), ("depart", "sched_depart")]
        for t_key, s_key in timing_keys:
            timing = stop.get(t_key)
            sched_ts = stop.get(s_key)
            if not isinstance(timing, dict) or sched_ts is None:
                continue
            variance = timing.get("variance") or 0
            try:
                return datetime.fromtimestamp(float(sched_ts) + float(variance), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                continue
        return None

    def _stop_delay_min(self, stop: dict) -> int:
        """Return delay in minutes from the most relevant timing object."""
        for key in ("depart", "arrive"):
            timing = stop.get(key)
            if isinstance(timing, dict):
                return int((timing.get("variance") or 0) / 60)
        return 0

    def _bearing_to_heading(self, bearing: float) -> str:
        dirs = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        idx = int((float(bearing) % 360.0) / 45.0 + 0.5) % len(dirs)
        return dirs[idx]

    def _refresh_if_needed(self):
        now = time.time()
        with self._lock:
            if now - self._cache_ts < self.CACHE_SEC:
                return

        map_data = self._fetch_json("map")
        station_data = self._fetch_json("stationInfo")
        if not isinstance(map_data, list) or not isinstance(station_data, list):
            return

        station_by_code = {}
        stations = []
        for st in station_data:
            code = str(st.get("code") or "").strip().upper()
            lat = st.get("latitude")
            lon = st.get("longitude")
            if not code or lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue
            city = str(st.get("city") or "").strip()
            state = str(st.get("state") or "").strip()
            name = city if not state else f"{city}, {state}"
            station_obj = {
                "code": code,
                "name": name or code,
                "lat": lat,
                "lon": lon,
                "active": bool(st.get("active", True)),
                "show_on_map": bool(st.get("show_on_map", True)),
            }
            stations.append(station_obj)
            station_by_code[code] = station_obj

        trains = []
        tracks = []
        seen_segments = set()
        for raw in map_data:
            loc = raw.get("location") or {}
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            if lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
                speed = max(0.0, float(loc.get("speed") or 0.0))
                bearing = float(loc.get("heading") or 0.0)
            except (TypeError, ValueError):
                continue

            railroad = str(raw.get("railroad") or "").upper()
            number = str(raw.get("number") or "?")
            route_name = str(raw.get("name") or f"{railroad} {number}").strip()
            stops = raw.get("stops") or []

            train = {
                "provider": railroad,
                "trainNum": number,
                "routeName": route_name,
                "lat": lat,
                "lon": lon,
                "velocity": speed,
                "heading": self._bearing_to_heading(bearing),
                "iconColor": self.PROVIDER_COLORS.get(railroad, "#e8a020"),
                "origin_code": str(raw.get("origin") or "").upper(),
                "destination_code": str(raw.get("destination") or "").upper(),
                "total_miles": int(raw.get("total_miles") or 0),
                "stops": stops,
            }
            trains.append(train)

            route_pts = []
            for stop in stops:
                code = str(stop.get("code") or "").strip().upper()
                st = station_by_code.get(code)
                if not st:
                    continue
                route_pts.append((st["lat"], st["lon"]))

            for i in range(len(route_pts) - 1):
                a = route_pts[i]
                b = route_pts[i + 1]
                if haversine_miles(a[0], a[1], b[0], b[1]) > 450:
                    continue
                k1 = (round(a[0], 4), round(a[1], 4))
                k2 = (round(b[0], 4), round(b[1], 4))
                key = (k1, k2) if k1 <= k2 else (k2, k1)
                if key in seen_segments:
                    continue
                seen_segments.add(key)
                tracks.append({"points": [a, b]})

        with self._lock:
            self._cache = {
                "trains": trains,
                "stations": stations,
                "station_by_code": station_by_code,
                "tracks": tracks,
            }
            self._cache_ts = time.time()

    def _snapshot(self):
        self._refresh_if_needed()
        with self._lock:
            return self._cache.copy()

    def get_infrastructure(self, bbox):
        min_lat, min_lon, max_lat, max_lon = bbox
        snap = self._snapshot()
        stations = []
        for st in snap["stations"]:
            if not st.get("show_on_map", True):
                continue
            if min_lat <= st["lat"] <= max_lat and min_lon <= st["lon"] <= max_lon:
                stations.append(st)
        tracks = []
        for tr in snap["tracks"]:
            pts = tr.get("points", [])
            if len(pts) < 2:
                continue
            (a_lat, a_lon), (b_lat, b_lon) = pts[0], pts[-1]
            if (
                (min_lat <= a_lat <= max_lat and min_lon <= a_lon <= max_lon)
                or (min_lat <= b_lat <= max_lat and min_lon <= b_lon <= max_lon)
            ):
                tracks.append(tr)
        return {"tracks": tracks, "stations": stations}

    def get_trains_in_bbox(self, bbox):
        min_lat, min_lon, max_lat, max_lon = bbox
        snap = self._snapshot()
        return [
            t for t in snap["trains"]
            if min_lat <= t["lat"] <= max_lat and min_lon <= t["lon"] <= max_lon
        ]

    def _stop_name(self, station_by_code, code: str) -> str:
        st = station_by_code.get(code)
        if not st:
            return code
        return st.get("name", code)

    def _next_stop_name(self, train: dict, station_by_code: dict) -> str:
        now_utc = datetime.now(timezone.utc)
        for stop in train.get("stops", []):
            if stop.get("canceled"):
                continue
            est = self._stop_est_dt(stop)
            if est and est >= now_utc - timedelta(minutes=2):
                code = str(stop.get("code") or "").strip().upper()
                return self._stop_name(station_by_code, code)
        return "—"

    def _destination_name(self, train: dict, station_by_code: dict) -> str:
        code = str(train.get("destination_code") or "").strip().upper()
        if code:
            return self._stop_name(station_by_code, code)
        for stop in reversed(train.get("stops", [])):
            code = str(stop.get("code") or "").strip().upper()
            if code:
                return self._stop_name(station_by_code, code)
        return str(train.get("routeName") or "Unknown")

    def _station_distance(self, station_by_code: dict, code: str, fallback: float) -> float:
        st = station_by_code.get(code)
        if not st:
            return fallback
        return haversine_miles(ORIGIN_LAT, ORIGIN_LON, st["lat"], st["lon"])

    def _stop_status(self, stop: dict, pred_dt: datetime, sch_dt: datetime, now_utc: datetime) -> str:
        if stop.get("canceled"):
            return "Canceled"
        if pred_dt < now_utc - timedelta(minutes=2):
            return "Departed"
        delay_min = self._stop_delay_min(stop)
        if delay_min > 2:
            return "Late"
        if delay_min < -2:
            return "Early"
        return "On Time"

    def get_nearby_schedule(self, radius_miles: float = SCHEDULE_RADIUS_MILES) -> list:
        snap = self._snapshot()
        station_by_code = snap["station_by_code"]
        now_utc = datetime.now(timezone.utc)
        entries = []

        for train in snap["trains"]:
            train_dist = haversine_miles(ORIGIN_LAT, ORIGIN_LON, train["lat"], train["lon"])
            if train_dist > radius_miles:
                continue

            num = train.get("trainNum", "?")
            route = train.get("routeName", "")
            destination = self._destination_name(train, station_by_code)
            next_stop = self._next_stop_name(train, station_by_code)
            direction = str(train.get("heading") or "?")
            speed_mph = float(train.get("velocity") or 0.0)

            best_entry = None
            for stop in train.get("stops", []):
                if stop.get("canceled"):
                    continue
                code = str(stop.get("code") or "").strip().upper()
                pred_dt = self._stop_est_dt(stop)
                if pred_dt is None:
                    continue
                if pred_dt < now_utc - timedelta(minutes=2):
                    continue

                delay_min = self._stop_delay_min(stop)
                status = self._stop_status(stop, pred_dt, pred_dt, now_utc)
                dist = self._station_distance(station_by_code, code, train_dist)
                station_name = self._stop_name(station_by_code, code)
                sched_ts = stop.get("sched_depart") or stop.get("sched_arrive")
                sch_dt = self._to_dt(sched_ts) if sched_ts else pred_dt

                candidate = {
                    "train_num": num,
                    "route_name": route,
                    "station_name": station_name,
                    "station_code": code,
                    "sch_dep": sch_dt,
                    "est_dep": pred_dt,
                    "status": status,
                    "delay_min": delay_min,
                    "dist_miles": dist,
                    "train_lat": train["lat"],
                    "train_lon": train["lon"],
                    "origin_code": train.get("origin_code", ""),
                    "destination": destination,
                    "next_stop": next_stop,
                    "direction": direction,
                    "speed_mph": speed_mph,
                    "total_miles": train.get("total_miles", 0),
                }
                if best_entry is None or (candidate["est_dep"], candidate["dist_miles"]) < (
                    best_entry["est_dep"], best_entry["dist_miles"]
                ):
                    best_entry = candidate

            if best_entry is None:
                best_entry = {
                    "train_num": num,
                    "route_name": route,
                    "station_name": next_stop if next_stop != "—" else destination,
                    "station_code": "",
                    "sch_dep": None,
                    "est_dep": None,
                    "status": "Enroute",
                    "delay_min": 0,
                    "dist_miles": train_dist,
                    "train_lat": train["lat"],
                    "train_lon": train["lon"],
                    "origin_code": train.get("origin_code", ""),
                    "destination": destination,
                    "next_stop": next_stop,
                    "direction": direction,
                    "speed_mph": speed_mph,
                    "total_miles": train.get("total_miles", 0),
                }
            entries.append(best_entry)

        entries.sort(key=lambda e: (e["est_dep"] is None, e["est_dep"]))
        return entries


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

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.zoom = TILE_ZOOM
        self.tile_overlay = MapTileOverlay(OSM_TILE_URL)

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

        self._surface = pygame.Surface((width, height))
        self._static_surface = pygame.Surface((width, height))
        self._tone_overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self._tone_overlay.fill((0, 0, 0, 55))
        self._total_tiles = self.tiles_x * self.tiles_y
        self._tiles_drawn_last = 0
        self._static_cache_key = None
        self._last_static_refresh = 0.0
        self._tile_refresh_interval_sec = 0.5

        self._station_label_cache: dict[str, pygame.Surface] = {}
        self._num_font_small = pygame.font.Font(None, 15)
        self._num_font_large = pygame.font.Font(None, 18)
        self._train_num_cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface]] = {}

    def _render_static_layer(self, infrastructure: dict, font_small: pygame.font.Font):
        """Render static map parts: tiles, infrastructure, and fixed markers."""
        self._static_surface.fill(C_BG)

        tile_drawn = 0
        for dx in range(self.tiles_x):
            for dy in range(self.tiles_y):
                tx = self.origin_tile_x + dx
                ty = self.origin_tile_y + dy
                px = int(self._cx_px + (tx - self._origin_ftx) * TILE_SIZE)
                py = int(self._cy_px + (ty - self._origin_fty) * TILE_SIZE)
                tile = self.tile_overlay.get(self.zoom, tx, ty)
                if tile is not None:
                    self._static_surface.blit(tile, (px, py))
                    tile_drawn += 1
                else:
                    pygame.draw.rect(self._static_surface, (16, 22, 32), pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))

        if tile_drawn == 0:
            grid_color = (20, 28, 40)
            for gx in range(0, self.width, 64):
                pygame.draw.line(self._static_surface, grid_color, (gx, 0), (gx, self.height), 1)
            for gy in range(0, self.height, 64):
                pygame.draw.line(self._static_surface, grid_color, (0, gy), (self.width, gy), 1)

        self._tiles_drawn_last = tile_drawn
        self._static_surface.blit(self._tone_overlay, (0, 0))

        tracks = (infrastructure or {}).get("tracks", [])
        for tr in tracks:
            pts = tr.get("points", [])
            if len(pts) < 2:
                continue
            px_pts = []
            for lat, lon in pts:
                px, py = self._latlon_to_px(lat, lon)
                if -128 <= px <= self.width + 128 and -128 <= py <= self.height + 128:
                    px_pts.append((px, py))
            if len(px_pts) < 2:
                continue
            try:
                pygame.draw.lines(self._static_surface, (22, 28, 38), False, px_pts, 5)
                pygame.draw.lines(self._static_surface, (133, 158, 188), False, px_pts, 2)
            except Exception:
                continue

        for st in (infrastructure or {}).get("stations", []):
            slat = st.get("lat")
            slon = st.get("lon")
            sname = st.get("name", "")
            if slat is None or slon is None:
                continue
            px, py = self._latlon_to_px(slat, slon)
            if -10 <= px < self.width + 10 and -10 <= py < self.height + 10:
                pygame.draw.circle(self._static_surface, C_STATION_DOT, (px, py), 5)
                pygame.draw.circle(self._static_surface, C_TEXT, (px, py), 5, 1)
                lbl = self._station_label_cache.get(sname)
                if lbl is None:
                    lbl = font_small.render(sname, True, C_TEXT)
                    self._station_label_cache[sname] = lbl
                self._static_surface.blit(lbl, (px + 7, py - 6))

        ox, oy = self._latlon_to_px(ORIGIN_LAT, ORIGIN_LON)
        pygame.draw.circle(self._static_surface, C_ACCENT, (ox, oy), 8, 2)
        pygame.draw.line(self._static_surface, C_ACCENT, (ox - 14, oy), (ox + 14, oy), 1)
        pygame.draw.line(self._static_surface, C_ACCENT, (ox, oy - 14), (ox, oy + 14), 1)

        edge_px, _ = self._latlon_to_px(ORIGIN_LAT, ORIGIN_LON + MAP_RADIUS_MILES / (
            69.0 * math.cos(math.radians(ORIGIN_LAT))))
        radius_px = abs(edge_px - ox)
        if radius_px > 10:
            pygame.draw.circle(self._static_surface, C_PANEL_BORDER, (ox, oy), radius_px, 1)

        self._last_static_refresh = time.time()

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
               dest_xy: tuple[int, int] = (0, 0)) -> bool:
        """Draw map onto the provided surface. Returns True if the static layer was rebuilt."""
        tracks = (infrastructure or {}).get("tracks", [])
        stations = (infrastructure or {}).get("stations", [])
        static_key = (len(tracks), len(stations), font_small.get_height())

        now = time.time()
        needs_static_refresh = (self._static_cache_key != static_key)
        if not needs_static_refresh:
            _, pending_tiles = self.tile_overlay.get_stats()
            tile_incomplete = self._tiles_drawn_last < self._total_tiles
            if (pending_tiles > 0 or tile_incomplete) and (now - self._last_static_refresh) >= self._tile_refresh_interval_sec:
                needs_static_refresh = True

        if needs_static_refresh:
            self._render_static_layer(infrastructure, font_small)
            self._static_cache_key = static_key

        self._surface.blit(self._static_surface, (0, 0))

        # ── draw live Amtrak train positions ──────────────────────────
        for train in trains:
            tlat = train.get("lat")
            tlon = train.get("lon")
            if not tlat or not tlon:
                continue
            px, py = self._latlon_to_px(tlat, tlon)
            if -80 <= px < self.width + 80 and -80 <= py < self.height + 80:
                num      = str(train.get("trainNum", "?"))
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
                font_size = 15 if len(num) >= 3 else 18
                num_cached = self._train_num_cache.get((num, font_size))
                if num_cached is None:
                    num_font = self._num_font_small if font_size == 15 else self._num_font_large
                    num_cached = (
                        num_font.render(num, True, (255, 255, 255)),
                        num_font.render(num, True, (15, 15, 20)),
                    )
                    self._train_num_cache[(num, font_size)] = num_cached
                num_surf, num_dark = num_cached
                tx = px - num_surf.get_width() // 2
                ty = py - num_surf.get_height() // 2
                for odx, ody in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._surface.blit(num_dark, (tx + odx, ty + ody))
                self._surface.blit(num_surf, (tx, ty))

        surface.blit(self._surface, dest_xy)
        return needs_static_refresh

# ═══════════════════════════════════════════════════════════════════
# SECTION 8: SCHEDULE PANEL
# ═══════════════════════════════════════════════════════════════════

class SchedulePanel:
    """Displays ASM-style live train cards in a compact side drawer."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self._entries = []       # list of schedule entry dicts from TransitDocsClient
        self._last_update = 0
        self._page_started = time.time()
        self._base_panel = None
        self._rows_surface = None
        self._rows_cache_key = None
        self._cache_dirty = True
        self._progress_frac = 1.0
        self._last_progress_sample = 0.0

    def update(self, entries: list):
        """entries from TransitDocsClient.get_nearby_schedule()"""
        self._entries = entries[:]
        self._last_update = time.time()
        self._page_started = time.time()
        self._cache_dirty = True

    def _ensure_base_panel(self):
        r = self.rect
        if self._base_panel is not None:
            return
        panel = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        panel.fill((12, 17, 25, 214))
        pygame.draw.rect(panel, C_PANEL_BORDER, panel.get_rect(), 1, border_radius=12)
        self._base_panel = panel

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font, font_small: pygame.font.Font):
        r = self.rect
        self._ensure_base_panel()
        surface.blit(self._base_panel, r.topleft)

        y = r.top + 12
        x = r.left + 12
        content_w = r.width - 24
        now_ts = time.time()
        now_utc = datetime.now(timezone.utc)
        now_tick = int(now_ts)

        title = font_title.render("Intercity Rail Map", True, C_TEXT)
        subtitle = font_small.render("Live Trains Nearby", True, C_TEXT_DIM)
        surface.blit(title, (x, y))
        y += title.get_height() + 1
        surface.blit(subtitle, (x, y))
        y += subtitle.get_height() + 8
        pygame.draw.line(surface, C_SEPARATOR, (x, y), (x + content_w, y), 1)
        y += 8

        if self._entries:
            row_h = 52
            footer_h = 30
            available_h = max(0, (r.bottom - footer_h) - y)
            rows_per_page = max(1, available_h // row_h)
            total_pages = max(1, math.ceil(len(self._entries) / rows_per_page))
            elapsed = max(0.0, now_ts - self._page_started)
            page_idx = int(elapsed / SCHEDULE_PAGE_ROTATE_SEC) % total_pages
            page_start = page_idx * rows_per_page
            page_entries = self._entries[page_start:page_start + rows_per_page]

            row_signature = tuple(
                (
                    str(e.get("train_num", "?")),
                    str(e.get("route_name", "")),
                    str(e.get("origin_code", "")),
                    str(e.get("destination", "?")),
                    str(e.get("status", "")),
                    int(e.get("delay_min", 0)),
                    str(e.get("direction", "?")),
                    int(float(e.get("speed_mph") or 0.0)),
                )
                for e in page_entries
            )
            rows_cache_key = (page_idx, rows_per_page, row_signature)

            if self._cache_dirty or self._rows_cache_key != rows_cache_key or self._rows_surface is None:
                rows_surface = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                row_y = y
                for entry in page_entries:
                    num         = str(entry.get("train_num", "?"))
                    route       = entry.get("route_name", "")
                    origin_code = str(entry.get("origin_code", "") or "")
                    destination = str(entry.get("destination", "?"))
                    status      = entry.get("status", "")
                    delay       = entry.get("delay_min", 0)
                    direction   = str(entry.get("direction", "?"))
                    speed_mph   = float(entry.get("speed_mph") or 0.0)

                    card = pygame.Rect(x - r.left, row_y - r.top, content_w, 46)
                    pygame.draw.rect(rows_surface, (20, 27, 37), card, border_radius=8)
                    pygame.draw.rect(rows_surface, (50, 67, 88), card, 1, border_radius=8)

                    row1 = font_body.render(f"#{num}  {route[:20]}", True, C_TEXT)
                    route_str = f"{origin_code} → {destination[:18]}" if origin_code else f"→ {destination[:20]}"
                    row2 = font_small.render(
                        f"{route_str}  •  {speed_mph:.0f} mph {direction}",
                        True, C_TEXT_DIM
                    )
                    rows_surface.blit(row1, (card.left + 10, card.top + 5))
                    rows_surface.blit(row2, (card.left + 10, card.top + 27))

                    if status == "Departed":
                        chip_bg = (66, 76, 90)
                        chip_fg = (214, 221, 230)
                    elif delay > 15:
                        chip_bg = (145, 49, 49)
                        chip_fg = (255, 234, 234)
                    elif delay > 5:
                        chip_bg = (122, 85, 20)
                        chip_fg = (255, 233, 188)
                    elif delay < -2:
                        chip_bg = (25, 92, 69)
                        chip_fg = (212, 252, 237)
                    else:
                        chip_bg = (32, 96, 62)
                        chip_fg = (220, 249, 230)

                    delay_tag = f"+{delay}m" if delay > 2 else (f"{delay}m" if delay < -2 else "")
                    chip_text = ((status or "On Time") + (" " + delay_tag if delay_tag else "")).strip()[:14]
                    chip = font_small.render(chip_text, True, chip_fg)
                    chip_pad_x = 8
                    chip_pad_y = 3
                    chip_rect = pygame.Rect(
                        card.right - chip.get_width() - (chip_pad_x * 2) - 8,
                        card.top + 6,
                        chip.get_width() + (chip_pad_x * 2),
                        chip.get_height() + (chip_pad_y * 2),
                    )
                    pygame.draw.rect(rows_surface, chip_bg, chip_rect, border_radius=10)
                    rows_surface.blit(chip, (chip_rect.left + chip_pad_x, chip_rect.top + chip_pad_y))
                    row_y += 52

                self._rows_surface = rows_surface
                self._rows_cache_key = rows_cache_key
                self._cache_dirty = False

            surface.blit(self._rows_surface, r.topleft)

            if total_pages > 1:
                page_label = font_small.render(
                    f"Page {page_idx + 1}/{total_pages}", True, C_TEXT_DIM
                )
                surface.blit(page_label, (r.right - page_label.get_width() - 12, r.bottom - page_label.get_height() - 8))

        else:
            msg = font_body.render("Loading live train cards…", True, C_TEXT_DIM)
            surface.blit(msg, (x, y + 6))

        if self._last_update:
            ts = time.strftime("%H:%M:%S", time.localtime(self._last_update))
            upd = font_small.render(f"Updated {ts}", True, C_TEXT_DIM)
            surface.blit(upd, (x, r.bottom - upd.get_height() - 8))

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
        self._scroll_train_sprite = _load_whimsical_train_sprite(target_h=56)
        self._line_cache_key = None
        self._line_surfaces = []
        self._progress_frac = 1.0
        self._last_progress_sample = 0.0

    def update(self):
        if time.time() - self._last_rotate >= MOTD_ROTATE_SEC:
            self._index = (self._index + 1) % len(self._facts)
            if self._index == 0:
                random.shuffle(self._facts)
            self._current = self._facts[self._index]
            self._last_rotate = time.time()
            self._line_cache_key = None

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font):
        r = self.rect
        pygame.draw.rect(surface, C_MOTD_BG, r)
        pygame.draw.rect(surface, C_MOTD_BORDER, r, 2)

        y = r.top + 8
        title = font_title.render("◈ TRAIN FACT", True, C_ACCENT)
        surface.blit(title, (r.left + 10, y))
        y += title.get_height() + 6

        # Cache wrapped/rendered fact lines until content or panel width changes.
        line_cache_key = (self._current, r.width, font_body.get_height())
        if self._line_cache_key != line_cache_key:
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
            self._line_surfaces = [font_body.render(ln, True, C_TEXT) for ln in lines]
            self._line_cache_key = line_cache_key

        for lbl in self._line_surfaces:
            if y + lbl.get_height() > r.bottom - 8:
                break
            surface.blit(lbl, (r.left + 12, y))
            y += lbl.get_height() + 2

        # countdown bar with sprite leader
        now_ts = time.time()
        elapsed = now_ts - self._last_rotate
        progress_step_sec = 1.0 / max(1, PROGRESS_UPDATE_HZ)
        if (now_ts - self._last_progress_sample) >= progress_step_sec:
            self._progress_frac = min(1.0, elapsed / MOTD_ROTATE_SEC)
            self._last_progress_sample = now_ts
        frac = self._progress_frac
        track_l = r.left + 10
        track_r = r.right - 10
        track_y = r.bottom - 6
        progress_x = track_l + int((track_r - track_l) * (1.0 - frac))
        pygame.draw.line(surface, C_SEPARATOR, (track_l, track_y), (track_r, track_y), 2)
        pygame.draw.line(surface, C_ACCENT, (track_l, track_y), (progress_x, track_y), 3)
        if self._scroll_train_sprite is not None:
            sw = self._scroll_train_sprite.get_width()
            sx = progress_x - (sw // 2)
            sy = track_y - self._scroll_train_sprite.get_height() + 1
            # clip the blit to the panel rect so the sprite never bleeds outside
            clip_rect = pygame.Rect(r.left, r.top, r.width, r.height)
            old_clip = surface.get_clip()
            surface.set_clip(clip_rect)
            surface.blit(self._scroll_train_sprite, (sx, sy))
            surface.set_clip(old_clip)
        else:
            pygame.draw.circle(surface, C_ACCENT2, (progress_x, track_y), 4)

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
        self._repo_dir = os.path.dirname(os.path.abspath(__file__))
        self._next_self_update_check = time.time() + SELF_UPDATE_INTERVAL_S

        # fonts
        self._init_fonts()

        # ASM-style layout: full-screen map + floating cards
        self.map_rect = pygame.Rect(0, 0, self.screen_w, self.screen_h)
        self.header_rect = pygame.Rect(PANEL_GAP, PANEL_GAP, min(560, self.screen_w - (PANEL_GAP * 2)), 74)
        drawer_w = min(440, int(self.screen_w * 0.32))
        fact_h = max(150, min(200, int(self.screen_h * 0.18)))
        self.schedule_rect = pygame.Rect(
            self.screen_w - drawer_w - PANEL_GAP,
            PANEL_GAP,
            drawer_w,
            self.screen_h - (PANEL_GAP * 3) - fact_h
        )
        self.motd_rect = pygame.Rect(
            self.screen_w - drawer_w - PANEL_GAP,
            self.screen_h - PANEL_GAP - fact_h,
            drawer_w,
            fact_h
        )

        # subsystems
        self.transitdocs = TransitDocsClient()
        self.map_renderer = MapRenderer(self.map_rect.width, self.map_rect.height)
        self.schedule_panel = SchedulePanel(self.schedule_rect)
        self.motd_panel = MotdPanel(self.motd_rect)

        # cached surfaces for panels that don't change every frame
        self._header_surface: pygame.Surface | None = None
        self._header_cache_key = None
        self._footer_surface: pygame.Surface | None = None
        # composited background (map + static panels) written once per data update
        self._bg_surface: pygame.Surface | None = None
        self._bg_dirty = True

        # data state
        self._amtrak_trains = []   # live train positions for map
        self._infrastructure = {"tracks": [], "stations": []}
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

        self.font_title = pygame.font.SysFont(body_font, 22, bold=True) if body_font else pygame.font.Font(None, 24)
        self.font_body = pygame.font.SysFont(body_font, 17) if body_font else pygame.font.Font(None, 19)
        self.font_fact = pygame.font.SysFont(body_font, 21) if body_font else pygame.font.Font(None, 24)
        self.font_small = pygame.font.SysFont(body_font, 14) if body_font else pygame.font.Font(None, 16)
        self.font_clock = pygame.font.SysFont(body_font, 28, bold=True) if body_font else pygame.font.Font(None, 32)

    def _fetch_data(self):
        """Fetch Transitdocs data for map + information drawer."""
        amtrak_trains = self.transitdocs.get_trains_in_bbox(self._bbox)
        amtrak_sched = self.transitdocs.get_nearby_schedule(MAP_RADIUS_MILES)
        infrastructure = self.transitdocs.get_infrastructure(self._bbox)

        with self._data_lock:
            if amtrak_trains is not None:
                self._amtrak_trains = amtrak_trains
                self._last_data_update = time.time()
            if infrastructure is not None:
                self._infrastructure = infrastructure
        if amtrak_sched:
            self.schedule_panel.update(amtrak_sched)
        self._bg_dirty = True

    def _schedule_data_update(self):
        t = threading.Thread(target=self._fetch_data, daemon=True)
        t.start()

    def _render_header(self):
        r = self.header_rect

        now = time.localtime()
        time_str = time.strftime("%H:%M:%S", now)
        date_str = time.strftime("%A, %B %d %Y", now)
        age = time.time() - self._last_data_update if self._last_data_update else -1
        status_key = "live" if age >= 0 and age < 120 else ("stale" if age >= 120 else "loading")
        cache_key = (time_str, date_str, status_key)

        if self._header_cache_key != cache_key or self._header_surface is None:
            header = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            header.fill((14, 20, 28, 214))
            pygame.draw.rect(header, C_PANEL_BORDER, header.get_rect(), 1, border_radius=12)

            title = self.font_small.render("ASM Intercity Rail", True, C_TEXT_DIM)
            time_surf = self.font_clock.render(time_str, True, C_TEXT)
            date_surf = self.font_small.render(date_str, True, C_TEXT_DIM)
            header.blit(title, (12, 7))
            header.blit(time_surf, (12, 20))
            header.blit(date_surf, (170, 49))

            loc = self.font_small.render(f"Frederick area · {MAP_RADIUS_MILES} mi", True, C_TEXT_DIM)
            header.blit(loc, (r.width - loc.get_width() - 12, 10))

            if status_key == "live":
                status = self.font_small.render("● Live", True, (104, 235, 138))
            elif status_key == "stale":
                status = self.font_small.render("● Stale", True, C_ACCENT2)
            else:
                status = self.font_small.render("○ Loading", True, C_TEXT_DIM)
            header.blit(status, (r.width - status.get_width() - 12, 31))

            self._header_surface = header
            self._header_cache_key = cache_key

        self.screen.blit(self._header_surface, r.topleft)

    def _render_footer_hint(self):
        if self._footer_surface is None:
            self._footer_surface = self.font_small.render(
                "Data: asm.transitdocs.com", True, (132, 146, 164)
            )

    def run(self):
        running = True
        last_update_check = 0
        # Track the second of the last header render so we only redraw it once/sec.
        _last_header_second = -1
        # Track when the progress bars last changed so we can skip redraws.
        _progress_interval = 1.0 / max(1, PROGRESS_UPDATE_HZ)
        _last_progress_draw = 0.0
        # Composite background surface (map + schedule rows + motd text).
        # Rebuilt only when data changes; progress bars / header blitted on top each tick.
        _composite: pygame.Surface = pygame.Surface((self.screen_w, self.screen_h))
        _composite_dirty = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            now = time.time()
            now_second = int(now)

            if now >= self._next_self_update_check:
                self._next_self_update_check = now + SELF_UPDATE_INTERVAL_S
                if _maybe_self_update_and_restart(self._repo_dir):
                    pygame.quit()
                    sys.exit(0)

            # schedule periodic data refresh
            if now - last_update_check >= TRAIN_UPDATE_SEC:
                self._schedule_data_update()
                last_update_check = now

            # ── decide what needs redrawing ──────────────────────────────
            header_changed = (now_second != _last_header_second)
            progress_changed = (now - _last_progress_draw) >= _progress_interval
            # Check if new map tiles have arrived since last composite build
            _, pending_tiles = self.map_renderer.tile_overlay.get_stats()
            tile_incomplete = self.map_renderer._tiles_drawn_last < self.map_renderer._total_tiles
            tiles_arrived = (pending_tiles == 0 and tile_incomplete)
            map_needs_redraw = self._bg_dirty or self.map_renderer._static_cache_key is None or tiles_arrived

            if self._bg_dirty or map_needs_redraw:
                _composite_dirty = True

            # Rebuild composite when map/data changed
            if _composite_dirty:
                _composite.fill(C_BG)
                with self._data_lock:
                    trains = self._amtrak_trains
                    infrastructure = self._infrastructure
                map_rebuilt = self.map_renderer.render(
                    _composite, infrastructure, trains,
                    self.font_body, self.font_small,
                    self.map_rect.topleft
                )
                # ensure footer surface is initialized, then blit into composite
                self._render_footer_hint()
                if self._footer_surface is not None:
                    _composite.blit(
                        self._footer_surface,
                        (PANEL_GAP, self.screen_h - self._footer_surface.get_height() - 8)
                    )
                self.motd_panel.update()
                _composite_dirty = False
                self._bg_dirty = False
                # force full screen copy
                self.screen.blit(_composite, (0, 0))
                # render schedule (has its own row-level cache)
                self.schedule_panel.render(
                    self.screen, self.font_title, self.font_body, self.font_small
                )
                self.motd_panel.render(self.screen, self.font_title, self.font_small)
                self._render_header()
                _last_header_second = now_second
                _last_progress_draw = now
                pygame.display.flip()
                self.clock.tick(FPS_CAP)
                continue

            # Nothing structural changed — only repaint regions that update each tick
            dirty_rects: list[pygame.Rect] = []

            if header_changed:
                self._render_header()
                dirty_rects.append(self.header_rect)
                _last_header_second = now_second

            if progress_changed:
                # Repaint schedule progress bar area
                sched_r = self.schedule_panel.rect
                prog_region = pygame.Rect(sched_r.left, sched_r.bottom - 20, sched_r.width, 20)
                self.screen.blit(_composite, prog_region.topleft, prog_region)
                self.schedule_panel.render(
                    self.screen, self.font_title, self.font_body, self.font_small
                )
                dirty_rects.append(sched_r)

                # Repaint motd progress bar area
                motd_r = self.motd_panel.rect
                self.motd_panel.update()
                self.motd_panel.render(self.screen, self.font_title, self.font_small)
                dirty_rects.append(motd_r)

                _last_progress_draw = now

            if dirty_rects:
                pygame.display.update(dirty_rects)

            self.clock.tick(FPS_CAP)

        pygame.quit()
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = TrainStationApp()
    app.run()
