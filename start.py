#!/usr/bin/env python3
"""
Simple startup script
Start backend and frontend (development mode)
"""

import subprocess
import sys
from pathlib import Path
from multiprocessing import Process
import time


def start_backend():
    """Start backend"""
    print("🚀 Start backend...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "discord_agents.fastapi_main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "--reload",
        ]
    )


def start_frontend():
    """Start frontend"""
    print("🎨 Start frontend...")
    frontend_dir = Path(__file__).parent / "frontend"

    # 等待後端啟動
    time.sleep(3)

    subprocess.run(["pnpm", "dev"], cwd=frontend_dir)


def main():
    """Main function"""
    print("🎯 Discord Agents starting...")

    # Check pnpm
    try:
        subprocess.run(["pnpm", "--version"], capture_output=True, check=True)
    except:
        print("❌ Please install pnpm: npm install -g pnpm")
        sys.exit(1)

    # Create processes
    backend_process = Process(target=start_backend)
    frontend_process = Process(target=start_frontend)

    try:
        # Start processes
        backend_process.start()
        frontend_process.start()

        print("🎉 Server started!")
        print("📍 Backend: http://localhost:8080")
        print("📍 Frontend: http://localhost:5173")
        print("📍 Press Ctrl+C to stop")

        # 等待進程
        backend_process.join()
        frontend_process.join()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.join()
        frontend_process.join()
        print("👋 Shutting down...")


if __name__ == "__main__":
    main()
