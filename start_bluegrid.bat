@echo off
title Blue Grid - Lakshadweep Multi-Energy Optimization Challenge
color 0b

echo ================================================================
echo   BLUE GRID - Lakshadweep Multi-Energy Optimization Platform
echo   Team: CODEQUADRANTS ^| Ocean Hackathon
echo ================================================================
echo.

echo [1/3] Starting Python FastAPI Compute Engine on port 8500...
start "Blue Grid - Engine (8500)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --port 8500 --host 127.0.0.1"
timeout /t 3 >nul

echo [2/3] Starting Express Gateway on port 3001...
start "Blue Grid - Gateway (3001)" cmd /k "cd /d %~dp0gateway && node src/index.js"
timeout /t 2 >nul

echo [3/3] Starting Next.js Web Planner on port 3000...
start "Blue Grid - Frontend (3000)" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 4 >nul

echo.
echo ================================================================
echo   All 3 services have been launched!
echo   Frontend:    http://localhost:3000
echo   Gateway:     http://127.0.0.1:3001/api/health
echo   Engine Docs: http://127.0.0.1:8500/docs
echo ================================================================
echo.

start http://localhost:3000
