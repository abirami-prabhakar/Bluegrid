"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  exportUrl,
  getHourly,
  getIslands,
  getLiveStatus,
  getMeta,
  getTopsis,
  optimize,
  simulate,
} from "../lib/api";

const PRESETS = [
  {
    name: "Reference",
    mix: { solar_kw: 2400, wind_kw: 1200, otec_kw: 400, bess_kwh: 8000 },
  },
  {
    name: "Zero-Outage",
    mix: { solar_kw: 3200, wind_kw: 3000, otec_kw: 680, bess_kwh: 16000 },
  },
  {
    name: "Solar + BESS",
    mix: { solar_kw: 3500, wind_kw: 0, otec_kw: 0, bess_kwh: 12000 },
  },
];

function inrCr(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `₹${(n / 1e7).toFixed(2)} Cr`;
}

// ---------------------------------------------------------------------------
// Visual Island Digital Twin Component
// ---------------------------------------------------------------------------
function DigitalTwin({ record, mix, isPlaying, onTogglePlay, onStep, frame, totalFrames }) {
  const hour = record?.hour_index ?? 0;
  const day = Math.floor(hour / 24) + 1;
  const hod = hour % 24;

  const solarKw = record?.solar_gen_kw ?? 0;
  const windKw = record?.wind_gen_kw ?? 0;
  const otecKw = record?.otec_net_kw ?? 0;
  const bessKwh = record?.bess_soc_kwh ?? 0;
  const unmetKw = record?.unmet_load_kw ?? 0;

  const solarFrac = Math.min(solarKw / Math.max(mix.solar_kw, 1), 1);
  const windFrac = Math.min(windKw / Math.max(mix.wind_kw, 1), 1);
  const socFrac = Math.min(bessKwh / Math.max(mix.bess_kwh, 1), 1);
  const isCharging = (record?.bess_charge_kw ?? 0) > 1;
  const isDischarging = (record?.bess_discharge_kw ?? 0) > 1;
  const isShortfall = unmetKw > 1;

  // Time-of-day dynamic sky
  const isDay = hod >= 6 && hod <= 18;
  const isGolden = (hod >= 5 && hod <= 7) || (hod >= 17 && hod <= 19);

  let skyClass = "from-slate-900 via-indigo-950 to-blue-950"; // night
  if (isGolden) {
    skyClass = "from-amber-500 via-rose-700 to-indigo-900"; // dawn/dusk
  } else if (isDay) {
    skyClass = "from-sky-400 via-cyan-500 to-blue-700"; // daylight
  }

  const bladeSpeed = windFrac > 0.05 ? `${Math.max(2.2 - windFrac * 1.7, 0.4)}s` : "0s";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Canvas Scene */}
      <div className={`relative h-64 bg-gradient-to-b ${skyClass} transition-colors duration-700 p-4 select-none overflow-hidden`}>
        {/* Stars at night */}
        {!isDay && (
          <div className="absolute inset-0 pointer-events-none opacity-60">
            <div className="absolute top-4 left-1/4 h-1 w-1 bg-white rounded-full animate-ping" />
            <div className="absolute top-12 left-1/2 h-1 w-1 bg-cyan-200 rounded-full" />
            <div className="absolute top-6 right-1/4 h-1.5 w-1.5 bg-amber-100 rounded-full" />
          </div>
        )}

        {/* Top Status Pill */}
        <div className="flex items-center justify-between z-20 relative">
          <div className="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-white/20 text-xs text-white">
            <span className="h-2 w-2 rounded-full bg-teal-400 animate-pulse" />
            <span className="font-semibold">Digital Twin Simulation</span>
            <span className="text-slate-300 text-[10px] hidden sm:inline">(1 MW Continuous Demand)</span>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-white/20 text-xs font-mono text-white">
            <span>Day {day}</span>
            <span className="text-slate-400">·</span>
            <span className="font-bold text-teal-300">{String(hod).padStart(2, "0")}:00</span>
          </div>
        </div>

        {/* Sun / Moon */}
        {isDay ? (
          <div
            className="absolute top-6 right-10 h-14 w-14 rounded-full bg-gradient-to-tr from-amber-400 to-yellow-200 sun-glow transition-all duration-500"
            style={{ opacity: 0.5 + solarFrac * 0.5 }}
          />
        ) : (
          <div className="absolute top-6 right-10 h-9 w-9 rounded-full bg-slate-100 shadow-[0_0_15px_rgba(255,255,255,0.5)]">
            <div className="absolute top-1 right-1 h-7 w-7 rounded-full bg-slate-900/70" />
          </div>
        )}

        {/* Solar Farm Graphic (Left) */}
        <div className="absolute left-6 bottom-16 z-10 flex flex-col items-center">
          <div className="flex gap-1.5 bg-slate-900/60 p-1.5 rounded-lg border border-white/20 backdrop-blur-sm shadow-md">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={`h-11 w-8 rounded border border-cyan-300/60 relative overflow-hidden transition-all ${
                  solarFrac > 0.05 ? "bg-gradient-to-br from-blue-700 to-indigo-950 shadow-md" : "bg-slate-800 opacity-60"
                }`}
              >
                <div className="absolute inset-0 grid grid-cols-2 grid-rows-3 gap-[1px] opacity-40">
                  {[...Array(6)].map((_, idx) => (
                    <div key={idx} className="border border-white/40" />
                  ))}
                </div>
                {solarFrac > 0.1 && <div className="absolute inset-0 bg-amber-400/25 animate-pulse" />}
              </div>
            ))}
          </div>
          {/* High-contrast crisp badge */}
          <div className="mt-1.5 text-xs font-mono bg-white text-slate-900 px-2.5 py-0.5 rounded-md font-bold shadow-md border border-slate-200 inline-flex items-center gap-1">
            <span className="text-amber-500">☀️</span> {Math.round(solarKw).toLocaleString()} kW
          </div>
        </div>

        {/* Offshore Wind Turbine (Center) */}
        <div className="absolute left-1/2 -translate-x-1/2 bottom-16 z-10 flex flex-col items-center">
          <div
            className="blades-spin relative h-16 w-16 flex items-center justify-center -mb-2"
            style={{ animationDuration: bladeSpeed, animationPlayState: windFrac > 0.05 ? "running" : "paused" }}
          >
            <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-md">
              <path d="M50 50 L48 8 Q50 4 52 8 L52 50 Z" fill="#ffffff" />
              <path d="M50 50 L14 71 Q11 73 14 76 L50 50 Z" fill="#f1f5f9" />
              <path d="M50 50 L86 71 Q89 73 86 76 L50 50 Z" fill="#e2e8f0" />
              <circle cx="50" cy="50" r="4.5" fill="#0f2a4a" stroke="#38bdf8" strokeWidth="1.5" />
            </svg>
          </div>
          <div className="w-1.5 h-14 bg-gradient-to-b from-slate-200 to-slate-400 rounded-sm shadow" />
          {/* High-contrast crisp badge */}
          <div className="mt-1.5 text-xs font-mono bg-white text-slate-900 px-2.5 py-0.5 rounded-md font-bold shadow-md border border-slate-200 inline-flex items-center gap-1">
            <span className="text-sky-500">💨</span> {Math.round(windKw).toLocaleString()} kW
          </div>
        </div>

        {/* Battery BESS (Right) */}
        <div className="absolute right-6 bottom-16 z-10 flex flex-col items-center">
          <div className="p-1.5 rounded-xl bg-white/95 border border-slate-200 backdrop-blur-md flex flex-col items-center shadow-md">
            <div className="h-11 w-7 rounded border-2 border-slate-400 p-0.5 relative overflow-hidden bg-slate-100">
              <div
                className={`absolute bottom-0 left-0 right-0 transition-all duration-300 rounded-sm ${
                  socFrac < 0.25 ? "bg-rose-500" : socFrac < 0.5 ? "bg-amber-400" : "bg-emerald-500"
                }`}
                style={{ height: `${Math.round(socFrac * 100)}%` }}
              />
              {isCharging && <div className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-900 font-bold">⚡</div>}
            </div>
            <span className="text-[10px] font-bold text-slate-800 font-mono mt-0.5">{Math.round(socFrac * 100)}%</span>
          </div>
          {/* High-contrast crisp badge */}
          <div className="mt-1.5 text-xs font-mono bg-white text-slate-900 px-2.5 py-0.5 rounded-md font-bold shadow-md border border-slate-200 inline-flex items-center gap-1">
            <span className="text-emerald-500">🔋</span> {Math.round(bessKwh).toLocaleString()} kWh
          </div>
        </div>

        {/* Ocean Surface & OTEC Deep Water Column (Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 h-14 bg-gradient-to-t from-cyan-950/95 to-cyan-800/40 border-t border-cyan-400/40 flex items-center justify-between px-5">
          <div className="ocean-pulse flex items-center gap-2">
            <span className="text-cyan-100 text-xs font-semibold">🌊 OTEC Ocean Plant</span>
            <span className="text-[10px] text-cyan-100 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-400/40 hidden sm:inline">
              1,000m Cold Water Pipe (ΔT: 22°C)
            </span>
          </div>
          <div className="text-xs font-mono text-cyan-100 font-semibold">
            OTEC Net: <b className="text-white font-bold">{Math.round(otecKw)} kW</b>
          </div>
        </div>
      </div>

      {/* Playback Controls & Load Status Bar */}
      <div className="bg-slate-50 px-4 py-2.5 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={onTogglePlay}
            className="h-8 px-3.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition flex items-center gap-1.5 shadow-sm"
          >
            {isPlaying ? "❚❚ Pause" : "▶ Play Timeline"}
          </button>
          <button
            onClick={onStep}
            className="h-8 px-3 rounded-lg border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 transition shadow-sm text-xs font-semibold"
          >
            +1 Hour
          </button>
        </div>

        {/* Timeline Scrubber */}
        <div className="flex-1 max-w-xs flex items-center gap-2">
          <input
            type="range"
            min={0}
            max={Math.max(totalFrames - 1, 0)}
            value={frame}
            onChange={(e) => onStep(Number(e.target.value))}
            className="w-full accent-teal-600 cursor-pointer"
          />
        </div>

        {/* Reliability Status Pill */}
        <div
          className={`px-3 py-1 rounded-full font-bold text-xs flex items-center gap-1.5 ${
            isShortfall
              ? "bg-rose-50 text-rose-700 border border-rose-300"
              : "bg-emerald-50 text-emerald-800 border border-emerald-300"
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${isShortfall ? "bg-rose-500 animate-ping" : "bg-emerald-500"}`} />
          {isShortfall ? `Shortfall: ${unmetKw.toFixed(0)} kW` : `1,000 kW Load Served (100% Clean)`}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Clean Stacked Area Generation Chart
// ---------------------------------------------------------------------------
function GenerationChart({ records }) {
  const maxVal = useMemo(() => {
    if (!records?.length) return 1500;
    const peak = Math.max(
      ...records.map((r) => (r.solar_gen_kw || 0) + (r.wind_gen_kw || 0) + (r.otec_net_kw || 0)),
      ...records.map((r) => r.load_kw || 1000),
      1200
    );
    return peak * 1.1;
  }, [records]);

  if (!records?.length) return null;

  const w = 700;
  const h = 180;
  const pad = { l: 40, r: 16, t: 16, b: 24 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const n = records.length;
  const x = (i) => pad.l + (i / Math.max(n - 1, 1)) * innerW;
  const y = (v) => pad.t + innerH - (Math.max(v, 0) / maxVal) * innerH;

  const withWind = records.map((r) => ({
    ...r,
    sw: (r.solar_gen_kw || 0) + (r.wind_gen_kw || 0),
    total: (r.solar_gen_kw || 0) + (r.wind_gen_kw || 0) + (r.otec_net_kw || 0),
  }));

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          Weekly Generation Mix (168 Hours)
        </h3>
        <div className="flex items-center gap-3 text-[11px] text-slate-600 font-medium">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" /> Solar</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-teal-500" /> Wind</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-500" /> OTEC</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-rose-500" /> 1 MW Load</span>
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-2 border border-slate-100">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[150px]">
          {/* 1,000 kW Load Reference Line */}
          <line
            x1={pad.l}
            y1={y(1000)}
            x2={w - pad.r}
            y2={y(1000)}
            stroke="#f43f5e"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />

          {/* OTEC Layer */}
          <polygon
            points={
              withWind.map((r, i) => `${x(i)},${y(r.total)}`).join(" ") +
              " " +
              withWind.map((r, i) => `${x(n - 1 - i)},${y(r.sw)}`).join(" ")
            }
            fill="#38bdf8"
            opacity="0.8"
          />

          {/* Wind Layer */}
          <polygon
            points={
              withWind.map((r, i) => `${x(i)},${y(r.sw)}`).join(" ") +
              " " +
              withWind.map((r, i) => `${x(n - 1 - i)},${y(r.solar_gen_kw || 0)}`).join(" ")
            }
            fill="#2dd4bf"
            opacity="0.85"
          />

          {/* Solar Layer */}
          <polygon
            points={
              records.map((r, i) => `${x(i)},${y(r.solar_gen_kw || 0)}`).join(" ") +
              " " +
              records.map((_, i) => `${x(n - 1 - i)},${y(0)}`).join(" ")
            }
            fill="#f59e0b"
            opacity="0.9"
          />

          {/* Labels */}
          <text x={pad.l} y={h - 6} fontSize="9" fill="#64748b">Hour 0 (Monday)</text>
          <text x={w - pad.r - 80} y={h - 6} fontSize="9" fill="#64748b">Hour 168 (Sunday)</text>
          <text x={w - pad.r - 95} y={y(1000) - 5} fontSize="9" fill="#e11d48" fontWeight="600">
            1,000 kW AC Load
          </text>
        </svg>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Light-Theme Planner Dashboard
// ---------------------------------------------------------------------------
export default function Planner() {
  const [island, setIsland] = useState("kadmat");
  const [islands, setIslands] = useState({});
  const [mix, setMix] = useState(PRESETS[0].mix);
  const [result, setResult] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [topsis, setTopsis] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [frame, setFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [opt, setOpt] = useState(null);
  const [showTopsis, setShowTopsis] = useState(false);

  useEffect(() => {
    getIslands().then((d) => setIslands(d.islands || {})).catch(() => {});
  }, []);

  const run = useCallback(async (nextMix = mix, nextIsland = island) => {
    setBusy("Running 8,760h simulation…");
    setError("");
    try {
      const body = { island: nextIsland, ...nextMix };
      const sim = await simulate(body);
      setResult(sim);

      const h = await getHourly(nextIsland, 168);
      setHourly(h.records || []);
      setFrame(0);
    } catch (e) {
      setError(e.message || "Failed to communicate with simulation engine");
    } finally {
      setBusy("");
    }
  }, [mix, island]);

  useEffect(() => {
    run(PRESETS[0].mix, "kadmat");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Animation playback
  useEffect(() => {
    if (!isPlaying || !hourly.length) return;
    const timer = setInterval(() => {
      setFrame((f) => (f + 1) % hourly.length);
    }, 280);
    return () => clearInterval(timer);
  }, [isPlaying, hourly.length]);

  async function handleOptimize() {
    setBusy("Solving optimal capacity with PuLP CBC algorithm…");
    setError("");
    try {
      const out = await optimize(island);
      setOpt(out);
      if (out.best) {
        const next = {
          solar_kw: out.best.solar_kw,
          wind_kw: out.best.wind_kw,
          otec_kw: out.best.otec_kw,
          bess_kwh: out.best.bess_kwh,
        };
        setMix(next);
        await run(next, island);
      }
    } catch (e) {
      setError(e.message || "Solver failed to find feasible mix");
    } finally {
      setBusy("");
    }
  }

  async function handleTopsis() {
    setShowTopsis(true);
    setBusy("Running TOPSIS MCDA evaluation…");
    try {
      const out = await getTopsis(island);
      setTopsis(out.ranked || []);
    } catch (e) {
      setError(e.message || "TOPSIS evaluation failed");
    } finally {
      setBusy("");
    }
  }

  const islandMeta = islands[island];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Application Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 sticky top-0 z-30 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-50 text-teal-700 border border-teal-200 flex items-center justify-center font-bold text-lg shadow-sm">
            🌊
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-lg font-bold text-slate-900 tracking-tight">
                Blue Grid
              </h1>
              <span className="bg-slate-100 text-slate-600 text-[11px] px-2.5 py-0.5 rounded-full border border-slate-200 font-medium">
                Lakshadweep Microgrid Planner
              </span>
            </div>
          </div>
        </div>

        {/* Island Selection & Direct Exports */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs shadow-sm">
            <span className="text-slate-500 font-medium">Island:</span>
            <select
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
              value={island}
              onChange={(e) => {
                const v = e.target.value;
                setIsland(v);
                run(mix, v);
              }}
            >
              {Object.keys(islands).length
                ? Object.entries(islands).map(([k, v]) => (
                    <option key={k} value={k} className="bg-white text-slate-900">
                      {v.name} ({v.latitude}°N)
                    </option>
                  ))
                : ["kadmat", "kavaratti", "minicoy"].map((k) => (
                    <option key={k} value={k} className="bg-white text-slate-900">
                      {k}
                    </option>
                  ))}
            </select>
          </div>

          <a
            href={exportUrl("pdf", island)}
            className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs px-3 py-1.5 rounded-lg transition font-semibold flex items-center gap-1 shadow-sm"
            target="_blank"
            rel="noreferrer"
          >
            📄 PDF Report
          </a>
          <a
            href={exportUrl("csv", island)}
            className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs px-3 py-1.5 rounded-lg transition font-semibold flex items-center gap-1 shadow-sm"
            target="_blank"
            rel="noreferrer"
          >
            📊 CSV
          </a>
        </div>
      </header>

      {/* Main Grid Layout */}
      <main className="flex-1 p-5 grid gap-5 lg:grid-cols-[310px_1fr_310px]">
        {/* Left Column: Sliders & Capacity Controls */}
        <section className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Capacity Sizing Sliders
              </h2>
              <span className="text-[11px] text-teal-800 bg-teal-50 px-2 py-0.5 rounded font-mono font-bold border border-teal-200">
                1 MW Load
              </span>
            </div>

            {/* Presets */}
            <div className="mb-4">
              <span className="text-[11px] text-slate-600 font-semibold block mb-1.5">Try a Preset Mix:</span>
              <div className="grid grid-cols-3 gap-1.5">
                {PRESETS.map((p) => (
                  <button
                    key={p.name}
                    onClick={() => {
                      setMix(p.mix);
                      run(p.mix, island);
                    }}
                    className="p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs text-center transition text-slate-800 font-semibold shadow-xs"
                  >
                    <div>{p.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* The 4 Core Energy Sliders */}
            <div className="space-y-3.5 mb-4">
              {/* Solar PV */}
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-800 font-semibold flex items-center gap-1.5">
                    ☀️ Solar PV
                  </span>
                  <span className="font-mono font-bold text-amber-600">{mix.solar_kw.toLocaleString()} kW</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={5000}
                  step={100}
                  value={mix.solar_kw}
                  onChange={(e) => setMix({ ...mix, solar_kw: Number(e.target.value) })}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>

              {/* Wind Energy */}
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-800 font-semibold flex items-center gap-1.5">
                    💨 Offshore Wind
                  </span>
                  <span className="font-mono font-bold text-teal-700">{mix.wind_kw.toLocaleString()} kW</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={3000}
                  step={100}
                  value={mix.wind_kw}
                  onChange={(e) => setMix({ ...mix, wind_kw: Number(e.target.value) })}
                  className="w-full accent-teal-600 cursor-pointer"
                />
              </div>

              {/* OTEC */}
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-800 font-semibold flex items-center gap-1.5">
                    🌊 OTEC Baseload
                  </span>
                  <span className="font-mono font-bold text-sky-700">{mix.otec_kw.toLocaleString()} kW</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1000}
                  step={50}
                  value={mix.otec_kw}
                  onChange={(e) => setMix({ ...mix, otec_kw: Number(e.target.value) })}
                  className="w-full accent-sky-600 cursor-pointer"
                />
              </div>

              {/* Battery BESS */}
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-800 font-semibold flex items-center gap-1.5">
                    🔋 Battery Storage
                  </span>
                  <span className="font-mono font-bold text-emerald-700">{mix.bess_kwh.toLocaleString()} kWh</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={16000}
                  step={500}
                  value={mix.bess_kwh}
                  onChange={(e) => setMix({ ...mix, bess_kwh: Number(e.target.value) })}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 pt-3 border-t border-slate-100">
            <button
              disabled={!!busy}
              onClick={() => run()}
              className="w-full rounded-xl bg-teal-600 text-white py-2.5 text-xs font-bold shadow hover:bg-teal-700 transition disabled:opacity-50"
            >
              {busy || "▶ Run 8,760h Simulation"}
            </button>
            <button
              disabled={!!busy}
              onClick={handleOptimize}
              className="w-full rounded-xl border border-teal-300 bg-teal-50 text-teal-900 py-2 text-xs font-bold hover:bg-teal-100 transition disabled:opacity-50"
            >
              ✨ Auto-Optimize (PuLP Algorithm)
            </button>
            <button
              disabled={!!busy}
              onClick={handleTopsis}
              className="w-full rounded-xl border border-slate-300 bg-white text-slate-800 py-2 text-xs font-semibold hover:bg-slate-50 transition disabled:opacity-50 shadow-xs"
            >
              ⚖️ TOPSIS Ranking Comparison
            </button>

            {islandMeta && (
              <p className="text-[10px] text-slate-600 pt-2 leading-relaxed border-t border-slate-100 font-medium">
                <b>{islandMeta.name}:</b> Mean wind {islandMeta.mean_wind_speed_ms} m/s · GHI {islandMeta.mean_ghi_kwh_m2_day} kWh/m²/day · SST {islandMeta.sea_surface_temp_c}°C / deep {islandMeta.deep_sea_temp_c}°C.
              </p>
            )}
          </div>
        </section>

        {/* Center Column: Visual Digital Twin & Weekly Generation Chart */}
        <section className="space-y-4">
          <DigitalTwin
            record={hourly[frame] || hourly[0]}
            mix={mix}
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            onStep={(target) => setFrame(typeof target === "number" ? target : (frame + 1) % hourly.length)}
            frame={frame}
            totalFrames={hourly.length}
          />

          <GenerationChart records={hourly} />
        </section>

        {/* Right Column: Analysis & Key Results */}
        <section className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              Microgrid Analysis
            </h2>

            {error && (
              <div className="p-2.5 mb-3 rounded-lg bg-rose-50 border border-rose-300 text-rose-800 text-xs font-medium">
                {error}
              </div>
            )}

            {/* Reliability Status Card */}
            {result && (
              <div
                className={`p-3 rounded-xl mb-3 border ${
                  result.lolp_pct <= 0.001
                    ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                    : "bg-amber-50 border-amber-300 text-amber-950"
                }`}
              >
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-700">
                  Grid Reliability (LOLP)
                </div>
                <div className="font-mono text-2xl font-black mt-0.5 text-slate-900">
                  {result.lolp_pct <= 0.001 ? "100.0% (0 Outages)" : `${(100 - result.lolp_pct).toFixed(2)}% Reliable`}
                </div>
                <div className="text-xs mt-1 text-slate-700 font-medium">
                  {result.lolp_pct <= 0.001
                    ? "Zero blackout risk across all 8,760 hours of the year!"
                    : `${result.shortfall_hours.toLocaleString()} shortfall hours during weather lulls.`}
                </div>
              </div>
            )}

            {/* Metrics List */}
            <div className="space-y-2.5">
              {/* LCOE */}
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-600 font-semibold">Clean Energy Cost (LCOE)</div>
                <div className="font-mono text-lg font-bold text-teal-800">
                  {result ? `₹${result.lcoe.toFixed(2)} / kWh` : "—"}
                </div>
                <div className="text-xs text-emerald-800 font-medium mt-0.5">
                  Replaces ₹22.50/unit diesel (saves ~₹{(22.5 - (result?.lcoe || 0)).toFixed(1)}/unit)
                </div>
              </div>

              {/* Diesel Subsidy Saved */}
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-600 font-semibold">Annual Diesel Subsidy Saved</div>
                <div className="font-mono text-lg font-bold text-slate-900">
                  {result ? inrCr(result.diesel_subsidy_avoided_inr_per_year) + " / yr" : "—"}
                </div>
                <div className="text-xs text-slate-600 font-medium">Government money saved from diesel logistics</div>
              </div>

              {/* CO2 Avoided */}
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-600 font-semibold">Carbon Emissions Avoided</div>
                <div className="font-mono text-lg font-bold text-slate-900">
                  {result ? `${Math.round(result.co2_avoided_tons_per_year).toLocaleString()} Tons / yr` : "—"}
                </div>
                <div className="text-xs text-slate-600 font-medium">Protects delicate Lakshadweep marine lagoons</div>
              </div>

              {/* CAPEX */}
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-600 font-semibold">Total Setup Investment (CAPEX)</div>
                <div className="font-mono text-lg font-bold text-slate-900">
                  {result ? inrCr(result.capex) : "—"}
                </div>
                <div className="text-xs text-slate-600 font-medium">Solar + Wind + OTEC + Battery assets</div>
              </div>
            </div>
          </div>

          <div className="mt-3 text-[11px] text-slate-500 text-center font-medium font-mono">
            Evaluated hour-by-hour over 8,760 hours
          </div>
        </section>
      </main>

      {/* Optional TOPSIS Benchmark Ranking Accordion / Card */}
      {showTopsis && (
        <section className="px-5 pb-5">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  TOPSIS Multi-Criteria Decision Analysis Ranking
                </h3>
                <p className="text-[11px] text-slate-600 font-medium">
                  Compares current design against standard island baselines (Cost vs Reliability vs Carbon)
                </p>
              </div>
              <button
                onClick={() => setShowTopsis(false)}
                className="text-slate-600 hover:text-slate-900 text-xs px-2.5 py-1 rounded bg-slate-100 border border-slate-200 transition font-semibold"
              >
                ✕ Close
              </button>
            </div>

            {opt?.best && (
              <div className="p-2.5 rounded-lg bg-teal-50 border border-teal-200 text-xs text-teal-950 mb-3 font-semibold">
                PuLP Algorithm Recommendation: Solar {opt.best.solar_kw} kW · Wind {opt.best.wind_kw} kW · OTEC {opt.best.otec_kw} kW · Battery {opt.best.bess_kwh} kWh (0.000% LOLP Blackout Risk)
              </div>
            )}

            {topsis.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left font-mono">
                  <thead>
                    <tr className="text-slate-600 border-b border-slate-200 pb-1.5 font-sans font-bold">
                      <th className="py-1">Rank</th>
                      <th>Configuration</th>
                      <th>Score</th>
                      <th>LCOE</th>
                      <th>Blackout %</th>
                      <th>CAPEX</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium">
                    {topsis.map((r) => (
                      <tr key={r.label} className={r.label === "current" ? "text-teal-900 font-bold bg-teal-50/70" : "text-slate-800"}>
                        <td className="py-2">#{r.rank}</td>
                        <td className="font-sans font-semibold">{r.label}</td>
                        <td>{r.topsis_score.toFixed(3)}</td>
                        <td>₹{r.lcoe.toFixed(2)}</td>
                        <td className={r.lolp > 0.5 ? "text-amber-700 font-bold" : "text-emerald-700 font-bold"}>
                          {r.lolp.toFixed(2)}%
                        </td>
                        <td>{inrCr(r.capex)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-slate-500 py-2">Loading ranking scores…</div>
            )}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="px-6 py-3 bg-white border-t border-slate-200 text-xs text-slate-500 flex flex-wrap items-center justify-between gap-2 font-medium">
        <div>
          Blue Grid · CODEQUADRANTS · Ocean Hackathon · UN SDGs 6, 7, 9, 13, 14
        </div>
        <div>
          Scientific References: PyPSA (2018) · TOPSIS (1981) · OTEC Cold Water Pipe Losses (2024) · NIOT Kavaratti Plant
        </div>
      </footer>
    </div>
  );
}
