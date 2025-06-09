#!/usr/bin/env python3
"""
Build frontend first, then start FastAPI backend (will serve static files automatically)
"""

import subprocess
import sys
import os
from pathlib import Path


def build_frontend():
    """Build frontend"""
    print("🎨 Build React frontend...")
    frontend_dir = Path(__file__).parent / "frontend"

    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False

    try:
        # Install dependencies (if needed)
        if not (frontend_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            install_result = subprocess.run(
                ["pnpm", "install"], cwd=frontend_dir, capture_output=True, text=True
            )
            if install_result.returncode != 0:
                print(f"❌ Installing dependencies failed: {install_result.stderr}")
                return False
            print("✅ Installing dependencies completed")

        # Build frontend
        print("🔨 Build frontend application...")
        build_result = subprocess.run(
            ["pnpm", "build"], cwd=frontend_dir, capture_output=True, text=True
        )

        if build_result.returncode != 0:
            print(f"❌ Build frontend failed: {build_result.stderr}")
            return False

        print("✅ Build frontend completed")
        return True

    except Exception as e:
        print(f"❌ Error building frontend: {e}")
        return False


def start_backend():
    """Start backend"""
    print("🚀 Start FastAPI backend server...")

    # Get port from environment variable, default to 8080
    port = os.getenv("PORT", "8080")

    try:
        # Use uvicorn to start, without reload mode
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "discord_agents.fastapi_main:app",
                "--host",
                "0.0.0.0",
                "--port",
                port,
                "--workers",
                "1",
            ]
        )

    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal, shutting down server...")
    except Exception as e:
        print(f"❌ Start backend failed: {e}")
        return False

    return True


def main():
    """Main function"""
    # Check if in the correct directory
    if not Path("discord_agents").exists():
        print("❌ Please run this script in the project root directory")
        sys.exit(1)

    # Skip frontend build if in Docker environment
    skip_frontend_build = os.getenv("SKIP_FRONTEND_BUILD", "").lower() in (
        "1",
        "true",
        "yes",
    )

    if not skip_frontend_build:
        # Check if pnpm is installed
        try:
            subprocess.run(["pnpm", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Please install pnpm: npm install -g pnpm")
            sys.exit(1)

        print("🎯 Discord Agents production environment starting...")
        print("=" * 50)

        # Build frontend
        if not build_frontend():
            print("❌ Build frontend failed, exiting")
            sys.exit(1)
    else:
        print("🎯 Discord Agents production environment starting (Docker mode)...")
        print("=" * 50)
        print("ℹ️ Skipping frontend build (using pre-built assets)")

    print("=" * 50)
    print("🎉 Prepare to start production environment!")
    print(f"📍 Application address: http://localhost:{os.getenv('PORT', '8080')}")
    print(f"📍 API docs: http://localhost:{os.getenv('PORT', '8080')}/api/docs")
    print("📍 Press Ctrl+C to stop server")
    print("=" * 50)

    # Start backend
    start_backend()

    print("👋 Server shut down")


if __name__ == "__main__":
    main()
