#!/usr/bin/env python3
"""
Use concurrent.futures to start the FastAPI backend and React frontend development servers concurrently
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class ConcurrentDevServer:
    def __init__(self) -> None:
        self.shutdown_event = threading.Event()
        self.processes: Dict[str, subprocess.Popen[str]] = {}

    def run_backend(self) -> str:
        """Run backend server"""
        print("🚀 [Backend] Start FastAPI backend server...")

        try:
            process = subprocess.Popen(
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
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["backend"] = process

            # 監控輸出
            while not self.shutdown_event.is_set():
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        print(f"[Backend] {line.strip()}")
                    elif process.poll() is not None:
                        break
                else:
                    break

            return "Backend completed"

        except Exception as e:
            print(f"❌ [Backend] Error: {e}")
            return f"Backend error: {e}"

    def run_frontend(self) -> str:
        """Run frontend development server"""
        print("🎨 [Frontend] Start React frontend development server...")
        frontend_dir = Path(__file__).parent / "frontend"

        if not frontend_dir.exists():
            return "Frontend directory not found"

        try:
            # Check dependencies
            if not (frontend_dir / "node_modules").exists():
                print("📦 [Frontend] Installing dependencies...")
                install_result = subprocess.run(
                    ["pnpm", "install"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                )
                if install_result.returncode != 0:
                    return f"Frontend install failed: {install_result.stderr}"
                print("✅ [Frontend] Dependencies installed")

            # Wait for backend to start
            time.sleep(2)

            process = subprocess.Popen(
                ["pnpm", "dev"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["frontend"] = process

            # Monitor output
            while not self.shutdown_event.is_set():
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        print(f"[Frontend] {line.strip()}")
                    elif process.poll() is not None:
                        break
                else:
                    break

            return "Frontend completed"

        except Exception as e:
            print(f"❌ [Frontend] Error: {e}")
            return f"Frontend error: {e}"

    def signal_handler(self, signum: int, frame: Any) -> None:
        """Handle interrupt signal"""
        print(f"\n🛑 Received signal {signum}, shutting down servers...")
        self.shutdown()

    def shutdown(self) -> None:
        """Shut down all servers"""
        self.shutdown_event.set()

        print("🔄 Shutting down all servers...")
        for name, process in self.processes.items():
            if process.poll() is None:
                print(f"🛑 Shutting down {name}...")
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print(f"⚠️  {name} force terminated...")
                        process.kill()
                        process.wait()
                    print(f"✅ {name} shut down")
                except Exception as e:
                    print(f"❌ Shutting down {name} error: {e}")

        print("👋 All servers shut down")

    def run(self) -> None:
        """Run servers using ThreadPoolExecutor"""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("🎯 Discord Agents development environment starting...")
        print("=" * 50)

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit tasks
                future_backend = executor.submit(self.run_backend)
                future_frontend = executor.submit(self.run_frontend)

                futures = {future_backend: "Backend", future_frontend: "Frontend"}

                print("🎉 Development environment started!")
                print("📍 Backend API: http://localhost:8080")
                print("📍 API docs: http://localhost:8080/api/docs")
                print("📍 Frontend app: http://localhost:5173")
                print("📍 Press Ctrl+C to stop all servers")
                print("=" * 50)

                # Wait for tasks to complete or interrupt
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        print(f"⚠️  {name} completed: {result}")
                    except Exception as e:
                        print(f"❌ {name} error: {e}")

                    # 如果任一服務器退出，關閉所有服務器
                    if not self.shutdown_event.is_set():
                        print(f"⚠️  {name} exited, shutting down all servers")
                        self.shutdown()
                        break

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"❌ Execution error: {e}")
            self.shutdown()


def main() -> None:
    """Main function"""
    # Check if in the correct directory
    if not Path("discord_agents").exists():
        print("❌ Please run this script in the project root directory")
        sys.exit(1)

    # Check if pnpm is installed
    try:
        subprocess.run(["pnpm", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Please install pnpm: npm install -g pnpm")
        sys.exit(1)

    # Start development servers
    dev_server = ConcurrentDevServer()
    dev_server.run()


if __name__ == "__main__":
    main()
