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

SCREEN_W = 1920  # unused — resolution is auto-detected at startup
SCREEN_H = 1080  # unused — resolution is auto-detected at startup
FPS_CAP = 20  # Pi B+: full screen rarely redraws; most ticks only touch the tiny motd rect

TRAIN_UPDATE_SEC = 30       # how often to refresh train positions
SCHEDULE_UPDATE_SEC = 30    # how often to refresh schedules
MOTD_ROTATE_SEC = 30        # how often to cycle train fact
SCHEDULE_PAGE_ROTATE_SEC = 10  # how often to flip Train Information pages
PROGRESS_UPDATE_HZ = 1          # progress bar update rate (Pi: keep it cheap)
SELF_UPDATE_INTERVAL_S = 5 * 60
SELF_UPDATE_TIMEOUT_S = 120

MAP_PANEL_W = int(SCREEN_W * 0.70)   # 1344 px
SIDE_PANEL_W = SCREEN_W - MAP_PANEL_W  # 576 px
BOTTOM_PANEL_H = 90
PANEL_GAP = 16

TILE_SIZE = 256             # OSM tile size in pixels
TILE_ZOOM = 9               # zoom level (9 zooms in a bit tighter on the origin area)
OSM_TILE_URL = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
RENDER_BOUNDS_MARGIN = 128  # pixels off-screen to render (for smooth scrolling)

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
_HEADING_ROT = {
    'E':  0, 'NE': 45, 'N':  90, 'NW': 135,
    'W': 180, 'SW': 225, 'S': 270, 'SE': 315,
}
# heading → (dx, dy) unit vector (used for motion trail offset)
_HEADING_VEC = {
    'N':  (0, -1),  'NE': ( 0.707, -0.707), 'E':  (1, 0),   'SE': ( 0.707, 0.707),
    'S':  (0,  1),  'SW': (-0.707,  0.707), 'W': (-1, 0),   'NW': (-0.707, -0.707),
}




class MapRenderer:
    """Renders the tiled map with railway overlay and train/station markers."""

    def __init__(self, width: int, height: int):
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

        self._surface = pygame.Surface((width, height))
        self._static_surface = pygame.Surface((width, height))
        self._static_cache_key = None

        self._station_label_cache: dict[str, pygame.Surface] = {}
        self._num_font_small = pygame.font.Font(None, 15)
        self._num_font_large = pygame.font.Font(None, 18)
        self._train_num_cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface]] = {}

        self._tile_base: pygame.Surface | None = None
        self._load_or_build_tile_base()

    def _load_or_build_tile_base(self):
        """Load pre-rendered map PNG or build it by downloading tiles, then save it."""
        map_path = f"map_{self.width}x{self.height}.png"
        if os.path.exists(map_path):
            self._tile_base = pygame.image.load(map_path).convert()
            return

        print(f"Building tile base {map_path} …", flush=True)
        surf = pygame.Surface((self.width, self.height))
        surf.fill((16, 22, 32))
        session = requests.Session()
        session.headers.update({
            "User-Agent": "TrainStationKiosk/1.0 (train enthusiast display; contact: kiosk@local)"
        })
        for dx in range(self.tiles_x):
            for dy in range(self.tiles_y):
                tx = self.origin_tile_x + dx
                ty = self.origin_tile_y + dy
                px = int(self._cx_px + (tx - self._origin_ftx) * TILE_SIZE)
                py = int(self._cy_px + (ty - self._origin_fty) * TILE_SIZE)
                url = OSM_TILE_URL.replace("{z}", str(self.zoom)).replace("{x}", str(tx)).replace("{y}", str(ty))
                try:
                    resp = session.get(url, timeout=15)
                    _log_http("GET", url, f"status={resp.status_code}")
                    if resp.status_code == 200:
                        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                        tile_surf = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
                        surf.blit(tile_surf, (px, py))
                    else:
                        pygame.draw.rect(surf, (16, 22, 32), pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))
                except Exception:
                    _log_http("GET", url, "error")
                    pygame.draw.rect(surf, (16, 22, 32), pygame.Rect(px, py, TILE_SIZE, TILE_SIZE))

        tone = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        tone.fill((0, 0, 0, 55))
        surf.blit(tone, (0, 0))
        pygame.image.save(surf, map_path)
        self._tile_base = surf.convert()

    def _render_static_layer(self, infrastructure: dict, font_small: pygame.font.Font):
        """Render static map parts: tile base, infrastructure, and fixed markers."""
        self._static_surface.fill(C_BG)
        self._static_surface.blit(self._tile_base, (0, 0))

        tracks = (infrastructure or {}).get("tracks", [])
        for tr in tracks:
            pts = tr.get("points", [])
            if len(pts) < 2:
                continue
            px_pts = []
            for lat, lon in pts:
                px, py = self._latlon_to_px(lat, lon)
                if (-RENDER_BOUNDS_MARGIN <= px < self.width + RENDER_BOUNDS_MARGIN and
                    -RENDER_BOUNDS_MARGIN <= py < self.height + RENDER_BOUNDS_MARGIN):
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
            if (-RENDER_BOUNDS_MARGIN <= px < self.width + RENDER_BOUNDS_MARGIN and
                -RENDER_BOUNDS_MARGIN <= py < self.height + RENDER_BOUNDS_MARGIN):
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

    def _latlon_to_px(self, lat, lon):
        """Convert lat/lon to pixel coordinates on the map surface.
        Uses consistent rounding to avoid cross-system precision differences."""
        lat_r = math.radians(lat)
        n = 2 ** self.zoom
        ftx = (lon + 180.0) / 360.0 * n
        fty = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
        px = self._cx_px + (ftx - self._origin_ftx) * TILE_SIZE
        py = self._cy_px + (fty - self._origin_fty) * TILE_SIZE
        return round(px), round(py)

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
        """Draw map (tile base, tracks, stations, trains) onto surface at dest_xy."""
        tracks = (infrastructure or {}).get("tracks", [])
        stations = (infrastructure or {}).get("stations", [])
        static_key = (len(tracks), len(stations), font_small.get_height())

        needs_static_refresh = (self._static_cache_key != static_key)
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
            if (-RENDER_BOUNDS_MARGIN <= px < self.width + RENDER_BOUNDS_MARGIN and
                -RENDER_BOUNDS_MARGIN <= py < self.height + RENDER_BOUNDS_MARGIN):
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


        self._surface.blit(self._static_surface, (0, 0))
        for train in trains:
            tlat = train.get("lat")
            tlon = train.get("lon")
            if not tlat or not tlon:
                continue
            px, py = self._latlon_to_px(tlat, tlon)
            if (-RENDER_BOUNDS_MARGIN <= px < self.width + RENDER_BOUNDS_MARGIN and
                -RENDER_BOUNDS_MARGIN <= py < self.height + RENDER_BOUNDS_MARGIN):
                num     = str(train.get("trainNum", "?"))
                heading = (train.get("heading") or "E").upper().strip()
                if heading not in _HEADING_ROT:
                    heading = "E"
                dot_color = _parse_hex_color(train.get("iconColor") or "#e8a020", (232, 160, 32))
                dot_r = 16 if len(num) >= 4 else (15 if len(num) == 3 else 14)
                vec = _HEADING_VEC.get(heading, _HEADING_VEC["E"])
                arrow_len = dot_r + 10
                ax0 = int(px + vec[0] * 4);  ay0 = int(py + vec[1] * 4)
                ax1 = int(px + vec[0] * arrow_len); ay1 = int(py + vec[1] * arrow_len)
                try:
                    pygame.draw.line(self._surface, (20, 20, 24), (ax0, ay0), (ax1, ay1), 4)
                    pygame.draw.line(self._surface, (250, 250, 250), (ax0, ay0), (ax1, ay1), 2)
                    head_left  = (int(ax1 - vec[0]*5 - vec[1]*4), int(ay1 - vec[1]*5 + vec[0]*4))
                    head_right = (int(ax1 - vec[0]*5 + vec[1]*4), int(ay1 - vec[1]*5 - vec[0]*4))
                    pygame.draw.polygon(self._surface, (20, 20, 24), [(ax1,ay1), head_left, head_right])
                    pygame.draw.polygon(self._surface, (250,250,250), [(ax1,ay1), head_left, head_right], 1)
                except Exception:
                    pass
                pygame.draw.circle(self._surface, (20, 20, 24), (px + 1, py + 1), dot_r + 1)
                pygame.draw.circle(self._surface, dot_color, (px, py), dot_r)
                pygame.draw.circle(self._surface, (255, 255, 255), (px, py), dot_r, 2)
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

# ═══════════════════════════════════════════════════════════════════
# SECTION 8: SCHEDULE PANEL
# ═══════════════════════════════════════════════════════════════════

class SchedulePanel:
    """Displays ASM-style live train cards in a compact side drawer."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self._entries = []
        self._last_update = 0
        self._page_started = time.time()
        self._cache_dirty = True
        # Single cached surface for the entire panel — rebuilt only on page/data change.
        self._full_surface: pygame.Surface | None = None
        self._full_cache_key = None

    def update(self, entries: list):
        self._entries = entries[:]
        self._last_update = time.time()
        self._page_started = time.time()
        self._cache_dirty = True

    def render(self, surface: pygame.Surface, font_title: pygame.font.Font,
               font_body: pygame.font.Font, font_small: pygame.font.Font):
        r = self.rect
        now_ts = time.time()

        # Determine current page
        row_h = 52
        footer_h = 30
        y_content_start = r.top + 12 + font_title.get_height() + 1 + font_small.get_height() + 16
        available_h = max(0, (r.bottom - footer_h) - y_content_start)
        rows_per_page = max(1, available_h // row_h)
        total_pages   = max(1, math.ceil(len(self._entries) / rows_per_page)) if self._entries else 1
        elapsed       = max(0.0, now_ts - self._page_started)
        page_idx      = int(elapsed / SCHEDULE_PAGE_ROTATE_SEC) % total_pages
        page_start    = page_idx * rows_per_page
        page_entries  = self._entries[page_start:page_start + rows_per_page]

        # Update minute (not second) so the timestamp doesn't bust the cache every tick
        update_minute = int(self._last_update // 60) if self._last_update else 0

        row_sig = tuple(
            (str(e.get("train_num")), str(e.get("route_name")), str(e.get("origin_code")),
             str(e.get("destination")), str(e.get("status")), int(e.get("delay_min", 0)),
             str(e.get("direction")), int(float(e.get("speed_mph") or 0)))
            for e in page_entries
        )
        cache_key = (page_idx, rows_per_page, row_sig, update_minute, bool(self._entries))

        if self._cache_dirty or self._full_cache_key != cache_key or self._full_surface is None:
            self._full_surface = self._build_surface(
                r, page_entries, page_idx, total_pages,
                font_title, font_body, font_small
            )
            self._full_cache_key = cache_key
            self._cache_dirty = False

        surface.blit(self._full_surface, r.topleft)

    def _build_surface(self, r, page_entries, page_idx, total_pages,
                       font_title, font_body, font_small):
        """Build the full panel surface. Called only on data/page changes."""
        surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        surf.fill((12, 17, 25, 214))
        pygame.draw.rect(surf, C_PANEL_BORDER, surf.get_rect(), 1, border_radius=12)

        x = 12
        y = 12
        content_w = r.width - 24

        title_s    = font_title.render("Intercity Rail Map", True, C_TEXT)
        subtitle_s = font_small.render("Live Trains Nearby", True, C_TEXT_DIM)
        surf.blit(title_s, (x, y));    y += title_s.get_height() + 1
        surf.blit(subtitle_s, (x, y)); y += subtitle_s.get_height() + 8
        pygame.draw.line(surf, C_SEPARATOR, (x, y), (x + content_w, y), 1)
        y += 8

        if page_entries:
            for entry in page_entries:
                num         = str(entry.get("train_num", "?"))
                route       = entry.get("route_name", "")
                origin_code = str(entry.get("origin_code", "") or "")
                destination = str(entry.get("destination", "?"))
                status      = entry.get("status", "")
                delay       = entry.get("delay_min", 0)
                direction   = str(entry.get("direction", "?"))
                speed_mph   = float(entry.get("speed_mph") or 0.0)

                card = pygame.Rect(x, y, content_w, 46)
                pygame.draw.rect(surf, (20, 27, 37), card, border_radius=8)
                pygame.draw.rect(surf, (50, 67, 88), card, 1, border_radius=8)

                row1 = font_body.render(f"#{num}  {route[:20]}", True, C_TEXT)
                route_str = f"{origin_code} → {destination[:18]}" if origin_code else f"→ {destination[:20]}"
                row2 = font_small.render(f"{route_str}  •  {speed_mph:.0f} mph {direction}", True, C_TEXT_DIM)
                surf.blit(row1, (card.left + 10, card.top + 5))
                surf.blit(row2, (card.left + 10, card.top + 27))

                if status == "Departed":   chip_bg, chip_fg = (66, 76, 90),   (214, 221, 230)
                elif delay > 15:           chip_bg, chip_fg = (145, 49, 49),  (255, 234, 234)
                elif delay > 5:            chip_bg, chip_fg = (122, 85, 20),  (255, 233, 188)
                elif delay < -2:           chip_bg, chip_fg = (25, 92, 69),   (212, 252, 237)
                else:                      chip_bg, chip_fg = (32, 96, 62),   (220, 249, 230)

                delay_tag = f"+{delay}m" if delay > 2 else (f"{delay}m" if delay < -2 else "")
                chip_text = ((status or "On Time") + (" " + delay_tag if delay_tag else "")).strip()[:14]
                chip_s = font_small.render(chip_text, True, chip_fg)
                cp_x, cp_y = 8, 3
                chip_rect = pygame.Rect(
                    card.right - chip_s.get_width() - cp_x * 2 - 8, card.top + 6,
                    chip_s.get_width() + cp_x * 2, chip_s.get_height() + cp_y * 2,
                )
                pygame.draw.rect(surf, chip_bg, chip_rect, border_radius=10)
                surf.blit(chip_s, (chip_rect.left + cp_x, chip_rect.top + cp_y))
                y += 52

            if total_pages > 1:
                page_s = font_small.render(f"Page {page_idx + 1}/{total_pages}", True, C_TEXT_DIM)
                surf.blit(page_s, (r.width - page_s.get_width() - 12, r.height - page_s.get_height() - 8))
        else:
            msg = font_body.render("Loading live train cards…", True, C_TEXT_DIM)
            surf.blit(msg, (x, y + 6))

        if self._last_update:
            ts  = time.strftime("%H:%M", time.localtime(self._last_update))
            upd = font_small.render(f"Updated {ts}", True, C_TEXT_DIM)
            surf.blit(upd, (x, r.height - upd.get_height() - 8))

        return surf

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
        self._line_cache_key = None
        self._line_surfaces = []

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


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

class TrainStationApp:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Train Station")

        info = pygame.display.Info()
        if info.current_w <= 0 or info.current_h <= 0:
            raise RuntimeError(f"Could not detect display resolution (got {info.current_w}x{info.current_h})")

        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((0, 0), flags)
        self.screen_w, self.screen_h = self.screen.get_size()

        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self._repo_dir = os.path.dirname(os.path.abspath(__file__))
        self._next_self_update_check = time.time() + SELF_UPDATE_INTERVAL_S

        # fonts
        self._init_fonts()

        # Layout: map on left, side panels on right — map does NOT overlap the side panel
        MAP_BORDER = 2          # px border drawn around the map
        MAP_PAD = PANEL_GAP     # padding between map border and side panel column
        drawer_w = min(440, int(self.screen_w * 0.32))
        fact_h = max(150, min(200, int(self.screen_h * 0.18)))
        header_h = 90

        # Side panel column starts at screen_w - drawer_w - PANEL_GAP
        side_col_x = self.screen_w - drawer_w - PANEL_GAP
        # Map occupies full height; its right edge leaves room for gap + border
        map_w = side_col_x - MAP_PAD - MAP_BORDER
        map_h = self.screen_h
        self.map_rect = pygame.Rect(0, 0, map_w, map_h)
        self.map_border_rect = pygame.Rect(0, 0, map_w + MAP_BORDER * 2, map_h + MAP_BORDER * 2)
        self._map_border_px = MAP_BORDER

        # Header sits at the top of the right-hand column
        self.header_rect = pygame.Rect(side_col_x, PANEL_GAP, drawer_w, header_h)

        # Schedule panel below the header
        sched_top = PANEL_GAP + header_h + PANEL_GAP
        self.schedule_rect = pygame.Rect(
            side_col_x,
            sched_top,
            drawer_w,
            self.screen_h - sched_top - PANEL_GAP * 2 - fact_h
        )
        self.motd_rect = pygame.Rect(
            side_col_x,
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
            # Only show trains whose current position is visible on the map
            min_lat, min_lon, max_lat, max_lon = self._bbox
            visible_sched = [
                e for e in amtrak_sched
                if min_lat <= e.get("train_lat", 0) <= max_lat
                and min_lon <= e.get("train_lon", 0) <= max_lon
            ]
            self.schedule_panel.update(visible_sched)

    def _schedule_data_update(self):
        t = threading.Thread(target=self._fetch_data, daemon=True)
        t.start()

    def _render_header(self):
        r = self.header_rect

        now = time.localtime()
        time_str = time.strftime("%H:%M", now)
        date_str = time.strftime("%A", now)
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
        last_render = 0.0
        RENDER_INTERVAL = 5.0

        while running:

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            now = time.time()

            if now >= self._next_self_update_check:
                self._next_self_update_check = now + SELF_UPDATE_INTERVAL_S
                if _maybe_self_update_and_restart(self._repo_dir):
                    pygame.quit()
                    sys.exit(0)

            if now - last_update_check >= TRAIN_UPDATE_SEC:
                self._schedule_data_update()
                last_update_check = now

            if now - last_render >= RENDER_INTERVAL:
                with self._data_lock:
                    trains = self._amtrak_trains[:]
                    infrastructure = self._infrastructure

                self.screen.fill(C_BG)
                self.map_renderer.render(
                    self.screen, infrastructure, trains,
                    self.font_body, self.font_small,
                    self.map_rect.topleft
                )
                b = self._map_border_px
                pygame.draw.rect(self.screen, C_PANEL_BORDER,
                                 pygame.Rect(self.map_rect.left, self.map_rect.top,
                                             self.map_rect.width, self.map_rect.height), b)
                self._render_footer_hint()
                if self._footer_surface is not None:
                    self.screen.blit(
                        self._footer_surface,
                        (PANEL_GAP, self.screen_h - self._footer_surface.get_height() - 8)
                    )
                self.motd_panel.update()
                self.schedule_panel.render(
                    self.screen, self.font_title, self.font_body, self.font_small
                )
                self.motd_panel.render(self.screen, self.font_title, self.font_small)
                self._render_header()
                pygame.display.flip()
                last_render = now

            self.clock.tick(FPS_CAP)

        pygame.quit()
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = TrainStationApp()
    app.run()
