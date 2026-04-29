# 🛰️ DebrisLens

**Real-time 3D visualization of every tracked object in Earth's orbit.**

DebrisLens is a live orbital tracker that streams the positions of satellites, rocket bodies, and space debris directly to an interactive 3D globe in your browser. Satellite positions are propagated in real-time using TLE data from [CelesTrak](https://celestrak.org) and served over WebSocket at 1 Hz.

---

## ✨ Features

- **Live 3D Globe** — Realistic Earth texture with atmosphere glow, rendered with Three.js
- **15,000+ Tracked Objects** — Active satellites, space stations, and debris from multiple CelesTrak datasets
- **Real-time Earth Rotation** — Globe rotates at true sidereal speed (GMST-aligned) so satellite positions match geography accurately
- **Click-to-Inspect** — Click any object to open a detail panel with:
  - Live latitude, longitude, and altitude (updated every second)
  - Orbit class (LEO / MEO / GEO)
  - Orbital parameters: NORAD ID, inclination, eccentricity, period, epoch
  - Public description fetched from Wikipedia (where available)
- **Chase Camera** — Lock the camera onto a selected satellite and follow it through its orbit
- **Hover Tooltip** — Quick-glance lat/lon/alt on mouseover
- **Color-coded Orbits**
  - 🔵 Cyan — LEO (< 2,000 km)
  - 🟡 Yellow — MEO (2,000 – 35,000 km)
  - 🔴 Red — GEO (> 35,000 km)
- **Auto-reconnect** — WebSocket reconnects automatically if the connection drops

---

## 🖥️ Tech Stack

| Layer     | Technology                           |
|-----------|--------------------------------------|
| Backend   | Python · FastAPI · Uvicorn           |
| Orbital math | Skyfield (SGP4/SDP4 propagation) |
| TLE data  | CelesTrak NORAD GP API               |
| Frontend  | Vanilla HTML/JS · Three.js r128      |
| Transport | WebSocket (JSON, 1 Hz)               |

---

## 🚀 Getting Started

### Prerequisites

```bash
pip install fastapi uvicorn skyfield
```

> `curl` must be available on your system (it is by default on macOS and most Linux distros).

### Run

```bash
cd DebrisLens
python3 main.py
```

Then open **[http://localhost:8000](http://localhost:8000)** in your browser.

On first launch, the server downloads TLE files from CelesTrak (takes ~5–10 seconds). Files are cached locally and reused on subsequent restarts.

---

## 📡 Data Sources

TLE datasets are fetched from CelesTrak's GP API at startup:

| Dataset              | Description                                   |
|----------------------|-----------------------------------------------|
| `GROUP=active`       | All active satellites (~15,000+ objects)       |
| `GROUP=stations`     | ISS, CSS, Tiangong, and other crewed stations  |
| `GROUP=debris`       | Catalogued debris fragments                    |
| `GROUP=cosmos-1408-debris` | Debris from Russia's 2021 ASAT test    |

Objects are deduplicated by NORAD catalog number.

---

## 📁 Project Structure

```
DebrisLens/
├── main.py        # FastAPI backend — TLE download, propagation, WebSocket feed
├── index.html     # Frontend — Three.js globe, UI panels, WebSocket client
├── active.txt     # Cached TLE data (auto-generated)
├── stations.txt   # Cached TLE data (auto-generated)
├── debris.txt     # Cached TLE data (auto-generated)
└── README.md
```

---

## 🎮 Controls

| Action              | Control                        |
|---------------------|--------------------------------|
| Rotate globe        | Left-click + drag              |
| Zoom                | Scroll wheel                   |
| Pan                 | Right-click + drag             |
| Inspect satellite   | Click on any dot               |
| Chase camera        | Click → "INITIATE CHASE CAM"   |
| Dismiss panel       | Click ✕ on the detail panel    |

---

## 🔬 How It Works

1. **Startup** — `main.py` fetches TLE files from CelesTrak using `curl` and parses them with Skyfield.
2. **WebSocket loop** — Every second, the server propagates all satellite positions to the current UTC time using SGP4/SDP4 and broadcasts a JSON array.
3. **Frontend** — The browser receives the array, converts geodetic coordinates (lat/lon/alt) to 3D Cartesian space, and updates a `THREE.Points` geometry buffer directly for maximum performance.
4. **Earth alignment** — The globe texture rotates in sync with Greenwich Mean Sidereal Time (GMST), ensuring satellite dots sit over the correct geographic location.

---

## ⚠️ Notes

- CelesTrak rate-limits requests to once every 2 hours per dataset. Cached `.txt` files are reused to stay within limits.
- Some TLE entries for decayed or maneuvering satellites may produce invalid positions and are silently filtered out.
- The `debris` dataset (~19,000 objects) may be rate-limited on the first fetch; it will be retried on the next server restart.

---

## 📄 License

MIT
