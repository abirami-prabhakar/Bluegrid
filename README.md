# Blue Grid — Lakshadweep Multi-Energy Optimization Challenge

Team: CODEQUADRANTS | Ocean Hackathon

Web platform for island planners to size a 100% renewable microgrid
(Solar + Wind + OTEC + BESS) that replaces diesel while holding a
continuous 1 MW AC load. Reliability is proven with an 8,760-hour
chronological dispatch (LOLP), not monthly averages.

## Tech stack

- Frontend: Next.js + TailwindCSS (`frontend/`)
- Gateway: Node.js / Express (`gateway/`) — Postgres + Redis
- Engine: Python FastAPI (`backend/`) — NumPy/Pandas dispatch, SciPy OTEC
  pumping & degradation, PuLP capacity mix LP, TOPSIS, ReportLab PDF/CSV
- Database: PostgreSQL + Redis (`docker-compose.yml`)
- Resource data: synthetic series shaped from published NIOT / Global Solar
  Atlas island profiles (live API credentials not configured)

## 7-step pipeline (do not reorder)

1. Resource Data Ingestion
2. Renewable Generation Model
3. Energy Mix Optimization
4. Battery Storage Simulation
5. Load & Reliability Check
6. Cost & Performance Analysis
7. Interactive Planner & Recommendation

## How to run

Copy environment defaults:

```bash
copy .env.example .env
```

### 1. Postgres + Redis

```bash
docker compose up -d
```

### 2. FastAPI engine (port 8500)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8500
```

### 3. Express gateway (port 3001)

```bash
cd gateway
npm install
npm run dev
```

### 4. Next.js planner (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The UI talks only to the Express gateway.
Swagger for the engine: `http://127.0.0.1:8500/docs`.

Reference mix on first load: Kadmat, Solar 2.4 MW / Wind 1.2 MW / OTEC 0.4 MW / Battery 8 MWh.

## What the engines actually do

- **OTEC net power**: Carnot-bounded gross output minus parasitic pumping
  `P = (ρ g Q H) / η_pump` with `g` from SciPy; not a flat 20–25% haircut.
- **Degradation**: PV `η(y) = (1 - 0.015)^y` and BESS SEI-style fade are
  applied in the yearly dispatch and the 20-year LCOE.
- **PuLP**: chronological capacity + dispatch LP, then the winner is
  re-checked with the NumPy 8,760-hour simulator.
- **LOLP**: indicator sum over every hour in the year.
- **Reports**: CAPEX, OPEX, LCOE, LOLP, TOPSIS vs baselines, four
  impact/benefit pairs, SDGs 6/7/9/13/14.

## Verified references (only these)

- PyPSA (Brown, Hörsch & Schlachtberger, 2018) — https://doi.org/10.5334/jors.188
- TOPSIS (Hwang & Yoon, 1981)
- OTEC cold-water-pipe losses (Aresti et al., ICTAM 2024) —
  https://ktisis.cut.ac.cy/handle/20.500.14279/33492
- Li-ion capacity fade at high temp (Carnovale & Li, 2020) —
  https://doi.org/10.1016/j.egyai.2020.100032
- NIOT OTEC-desalination plant, Kavaratti —
  https://www.drishtiias.com/daily-updates/daily-news-analysis/otec-plant-in-lakshadweep
