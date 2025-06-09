#!/usr/bin/env python3
"""
Start development environment script
Start FastAPI backend and React frontend development servers concurrently
"""

import subprocess
import sys
import signal
import time
import threading
from pathlib import Path


class DevServer:
    def __init__(self):
        self.processes = []
        self.running = True

    def start_backend(self):
        """Start FastAPI backend"""
        print("🚀 Start FastAPI backend server...")
        try:
            backend_process = subprocess.Popen(
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
                    "--no-access-log",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )
            self.processes.append(("Backend", backend_process))

            # 在背景執行緒中監控輸出
            def monitor_backend():
                for line in iter(backend_process.stdout.readline, ""):
                    if self.running:
                        print(f"[Backend] {line.strip()}")
                    else:
                        break

            threading.Thread(target=monitor_backend, daemon=True).start()
            return backend_process

        except Exception as e:
            print(f"❌ Start backend failed: {e}")
            return None

    def start_frontend(self):
        """Start React frontend development server"""
        print("🎨 Start React frontend development server...")
        frontend_dir = Path(__file__).parent / "frontend"

        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return None

        try:
            # 檢查是否有 node_modules
            if not (frontend_dir / "node_modules").exists():
                print("📦 Installing frontend dependencies...")
                install_process = subprocess.run(
                    ["pnpm", "install"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                )
                if install_process.returncode != 0:
                    print(
                        f"❌ Installing frontend dependencies failed: {install_process.stderr}"
                    )
                    return None
                print("✅ Installing frontend dependencies completed")

            frontend_process = subprocess.Popen(
                ["pnpm", "dev"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )
            self.processes.append(("Frontend", frontend_process))

            # Monitor output in background thread
            def monitor_frontend():
                for line in iter(frontend_process.stdout.readline, ""):
                    if self.running:
                        print(f"[Frontend] {line.strip()}")
                    else:
                        break

            threading.Thread(target=monitor_frontend, daemon=True).start()
            return frontend_process

        except Exception as e:
            print(f"❌ Start frontend failed: {e}")
            return None

    def signal_handler(self, signum, frame):
        """Handle interrupt signal"""
        print(f"\n🛑 Received signal {signum}, shutting down servers...")
        self.shutdown()

    def shutdown(self):
        """Shut down all processes"""
        self.running = False
        print("🔄 Shutting down all servers...")

        for name, process in self.processes:
            if process.poll() is None:  # Process is still running
                print(f"🛑 Shutting down {name}...")
                try:
                    process.terminate()
                    # Wait for process to exit, up to 5 seconds
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print(f"⚠️  {name} not closed normally, force terminated...")
                        process.kill()
                        process.wait()
                    print(f"✅ {name} shut down")
                except Exception as e:
                    print(f"❌ Shutting down {name} error: {e}")

        print("👋 All servers shut down")
        sys.exit(0)

    def run(self):
        """Run development servers"""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("🎯 Discord Agents development environment starting...")
        print("=" * 50)

        # Start backend
        backend = self.start_backend()
        if not backend:
            print("❌ Start backend failed, exiting")
            return

        # Wait for backend to start
        print("⏳ Waiting for backend to start...")
        time.sleep(3)

        # Start frontend
        frontend = self.start_frontend()
        if not frontend:
            print("❌ Start frontend failed, but backend is still running")

        print("=" * 50)
        print("🎉 Development environment started!")
        print("📍 Backend API: http://localhost:8080")
        print("📍 API docs: http://localhost:8080/api/docs")
        if frontend:
            print("📍 Frontend app: http://localhost:5173")
        print("📍 Press Ctrl+C to stop all servers")
        print("=" * 50)

        try:
            # 主執行緒等待
            while self.running:
                # 檢查進程是否還在運行
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(
                            f"⚠️  {name} exited unexpectedly (exit code: {process.returncode})"
                        )
                        if name == "Backend":
                            print("❌ Backend server exited, shutting down all servers")
                            self.shutdown()
                            return

                time.sleep(1)

        except KeyboardInterrupt:
            self.shutdown()


def main():
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
    dev_server = DevServer()
    dev_server.run()


if __name__ == "__main__":
    main()
