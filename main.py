import asyncio
import json
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from skyfield.api import load, EarthSatellite, wgs84

app = FastAPI(title="Live Satellite Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import HTMLResponse

# ---------------------------------------------------------------------------
# Load TLE data once at startup
# ---------------------------------------------------------------------------
satellites: list[EarthSatellite] = []

@app.get("/")
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.on_event("startup")
async def load_satellites():
    global satellites
    print("Downloading TLE data from Celestrak …")
    import subprocess
    import os
    import math

    # Groups to fetch — covers active payloads, debris, rocket bodies, and special interest
    groups = [
        ("active",   "active.txt"),
        ("stations", "stations.txt"),
        ("debris",   "debris.txt"),
        ("cosmos-1408-debris", "cosmos_debris.txt"),
    ]

    base_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
    all_sats = []

    for group, fname in groups:
        url = base_url.format(group=group)
        try:
            # Only re-download if file is missing or stale (< 500 bytes = error page)
            if not os.path.exists(fname) or os.path.getsize(fname) < 500:
                print(f"  Fetching {group}…")
                subprocess.run(
                    ["curl", "-s", "-o", fname, "-A", "Mozilla/5.0", url],
                    check=True, timeout=30
                )
            if os.path.exists(fname) and os.path.getsize(fname) > 500:
                sats = load.tle_file(fname)
                all_sats.extend(sats)
                print(f"  {group}: {len(sats)} objects")
            else:
                print(f"  {group}: skipped (rate limited or empty)")
        except Exception as e:
            print(f"  {group}: failed — {e}")

    # Deduplicate by NORAD ID (keep first occurrence)
    seen = set()
    unique = []
    for sat in all_sats:
        nid = sat.model.satnum
        if nid not in seen:
            seen.add(nid)
            unique.append(sat)

    satellites = unique
    print(f"Total loaded: {len(satellites)} unique objects.")



# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/satellites")
async def satellite_feed(websocket: WebSocket):
    await websocket.accept()
    ts = load.timescale()
    print("Client connected.")

    try:
        while True:
            t = ts.from_datetime(datetime.now(tz=timezone.utc))
            payload = []

            import math
            for sat in satellites:
                try:
                    geocentric = sat.at(t)
                    subpoint = wgs84.subpoint_of(geocentric)
                    lat = subpoint.latitude.degrees
                    lon = subpoint.longitude.degrees
                    alt = subpoint.elevation.km

                    if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
                        continue

                    # Extract orbital parameters from the SGP4 model
                    model = sat.model
                    # Period in seconds: 2π / (mean_motion in rad/s)
                    # mean_motion from TLE is in rev/day → rad/s
                    mean_motion_rad_s = model.no_kozai  # rad/min
                    period_s = (2 * math.pi / mean_motion_rad_s) * 60 if mean_motion_rad_s > 0 else None

                    # Epoch as ISO string
                    epoch_dt = sat.epoch.utc_datetime()
                    epoch_str = epoch_dt.strftime("%Y-%m-%d")

                    payload.append({
                        "name": sat.name,
                        "lat": round(lat, 4),
                        "lon": round(lon, 4),
                        "alt": round(alt, 2),
                        "norad": str(model.satnum),
                        "inc": round(math.degrees(model.inclo), 4),
                        "ecc": round(model.ecco, 7),
                        "period": round(period_s, 1) if period_s else None,
                        "epoch": epoch_str,
                    })
                except Exception:
                    continue

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as exc:
        print(f"WebSocket error: {exc}")


# ---------------------------------------------------------------------------
# Run with:  uvicorn main:app --reload
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)