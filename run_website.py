"""
Blue Grid — 1-Click Local Website Launcher for VS Code
Press the ▶ Play button in the top-right of VS Code or run:
    python run_website.py
"""
import subprocess
import time
import webbrowser
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
GATEWAY_DIR = os.path.join(ROOT_DIR, "gateway")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def main():
    print("=" * 70)
    print("  STARTING BLUE GRID WEBSITE (Lakshadweep Microgrid Platform)")
    print("=" * 70)

    # 1. Start Python FastAPI Backend Engine (Port 8500)
    print("\n[1/3] Starting Python FastAPI Engine on port 8500...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8500", "--host", "127.0.0.1"],
        cwd=BACKEND_DIR
    )
    time.sleep(2)

    # 2. Start Express Gateway (Port 3001)
    print("[2/3] Starting Express Gateway on port 3001...")
    gateway_proc = subprocess.Popen(
        ["node", "src/index.js"],
        cwd=GATEWAY_DIR,
        shell=True
    )
    time.sleep(2)

    # 3. Start Next.js Frontend (Port 3000)
    print("[3/3] Starting Next.js Web App on port 3000...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True
    )
    time.sleep(4)

    print("\n" + "=" * 70)
    print("  ALL SERVICES ARE RUNNING!")
    print("  -> Website:    http://localhost:3000")
    print("  -> Gateway:    http://127.0.0.1:3001/api/health")
    print("  -> Engine API: http://127.0.0.1:8500/docs")
    print("=" * 70)
    print("\nOpening http://localhost:3000 in your browser...")
    webbrowser.open("http://localhost:3000")

    print("\nPress Ctrl+C in this terminal anytime to stop all servers.")
    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down Blue Grid servers...")
        backend_proc.terminate()
        gateway_proc.terminate()
        frontend_proc.terminate()
        print("Done!")

if __name__ == "__main__":
    main()
