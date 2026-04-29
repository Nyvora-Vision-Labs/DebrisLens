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

# ---------------------------------------------------------------------------
# Load TLE data once at startup
# ---------------------------------------------------------------------------
satellites: list[EarthSatellite] = []

@app.on_event("startup")
async def load_satellites():
    global satellites
    print("Downloading TLE data from Celestrak …")
    try:
        url = "https://celestrak.org/SOCRATES/query.php?CODE=active&FORMAT=tle"
        # Use the built-in skyfield loader; fall back to a lighter dataset on error
        ts = load.timescale()
        try:
            sats = load.tle_file(
                "https://celestrak.org/SOCRATES/query.php?CODE=active&FORMAT=tle",
                reload=False,
            )
        except Exception:
            # Reliable fallback: visual stations (ISS + ~150 active birds)
            sats = load.tle_file(
                "https://celestrak.org/TLE/visual.txt",
                reload=False,
            )
        satellites = sats
        print(f"Loaded {len(satellites)} satellites.")
    except Exception as exc:
        print(f"Failed to load TLE data: {exc}")
        satellites = []


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

            for sat in satellites:
                try:
                    geocentric = sat.at(t)
                    subpoint = wgs84.subpoint_of(geocentric)
                    lat = subpoint.latitude.degrees
                    lon = subpoint.longitude.degrees
                    alt = subpoint.elevation.km
                    payload.append({
                        "name": sat.name,
                        "lat": round(lat, 4),
                        "lon": round(lon, 4),
                        "alt": round(alt, 2),
                    })
                except Exception:
                    # Skip satellites with propagation errors (decayed, bad TLE…)
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