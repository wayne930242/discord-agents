#!/usr/bin/env python3
"""
Docker container management script for Discord Agents
Provides functions to build, start, stop, and manage Docker containers
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Optional


class DockerManager:
    def __init__(self) -> None:
        self.container_name = "discord-agents"
        self.image_name = "discord-agents:latest"
        self.port = 8080
        self.host_port = 8080

    def run_command(
        self, cmd: list, capture_output: bool = True
    ) -> tuple[int, str, str]:
        """Execute a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd, capture_output=capture_output, text=True, check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_docker(self) -> bool:
        """Check if Docker is running"""
        print("🐳 Checking Docker status...")
        exit_code, _, _ = self.run_command(["docker", "--version"])
        if exit_code != 0:
            print("❌ Docker is not installed or not running")
            return False

        exit_code, _, _ = self.run_command(["docker", "info"])
        if exit_code != 0:
            print("❌ Docker daemon is not running")
            return False

        print("✅ Docker is ready")
        return True

    def build_image(self, tag: Optional[str] = None) -> bool:
        """Build Docker image"""
        if not tag:
            tag = self.image_name

        print(f"🔨 Building Docker image: {tag}")

        # Check if Dockerfile exists
        if not Path("Dockerfile").exists():
            print("❌ Dockerfile not found in current directory")
            return False

        exit_code, stdout, stderr = self.run_command(
            ["docker", "build", "-t", tag, "."], capture_output=False
        )

        if exit_code == 0:
            print(f"✅ Image built successfully: {tag}")
            return True
        else:
            print(f"❌ Failed to build image")
            return False

    def stop_container(self) -> bool:
        """Stop existing container"""
        print(f"🛑 Stopping container: {self.container_name}")

        # Check if container exists and is running
        exit_code, stdout, _ = self.run_command(
            ["docker", "ps", "-q", "--filter", f"name={self.container_name}"]
        )

        if exit_code == 0 and stdout.strip():
            exit_code, _, _ = self.run_command(["docker", "stop", self.container_name])
            if exit_code == 0:
                print(f"✅ Container stopped: {self.container_name}")
            else:
                print(f"❌ Failed to stop container: {self.container_name}")
                return False
        else:
            print(f"ℹ️  Container not running: {self.container_name}")

        return True

    def remove_container(self) -> bool:
        """Remove existing container"""
        print(f"🗑️  Removing container: {self.container_name}")

        # Check if container exists
        exit_code, stdout, _ = self.run_command(
            ["docker", "ps", "-aq", "--filter", f"name={self.container_name}"]
        )

        if exit_code == 0 and stdout.strip():
            exit_code, _, _ = self.run_command(["docker", "rm", self.container_name])
            if exit_code == 0:
                print(f"✅ Container removed: {self.container_name}")
            else:
                print(f"❌ Failed to remove container: {self.container_name}")
                return False
        else:
            print(f"ℹ️  Container does not exist: {self.container_name}")

        return True

    def start_container(
        self, detached: bool = True, host_port: Optional[int] = None
    ) -> bool:
        """Start Docker container"""
        if host_port:
            self.host_port = host_port

        print(f"🚀 Starting container: {self.container_name}")
        print(f"📍 Mapping port {self.host_port}:{self.port}")

        # Check if .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            print("❌ .env file not found")
            return False

        # Prepare Docker run command
        docker_cmd = [
            "docker",
            "run",
            "--name",
            self.container_name,
            "-p",
            f"{self.host_port}:{self.port}",
            "--env-file",
            ".env",
            "-e",
            "DATABASE_URL=postgresql://weihung@host.docker.internal:5432/discord_agents",
            "-e",
            "REDIS_URL=redis://host.docker.internal:6379",
            "-e",
            "DOCKER_CONTAINER=true",  # Flag for browser config detection
            "-v",
            f"{Path.cwd()}/data:/app/data",
            # Critical for Crawl4AI/Playwright in Docker
            "--shm-size=2g",  # Increase shared memory for browser stability
        ]

        if detached:
            docker_cmd.append("-d")

        docker_cmd.append(self.image_name)

        exit_code, stdout, stderr = self.run_command(
            docker_cmd, capture_output=detached
        )

        if exit_code == 0:
            if detached:
                print(f"✅ Container started successfully: {self.container_name}")
                print(f"📍 Application available at: http://localhost:{self.host_port}")
                print(
                    f"📍 API docs available at: http://localhost:{self.host_port}/api/docs"
                )
            return True
        else:
            print(f"❌ Failed to start container")
            if stderr:
                print(f"Error: {stderr}")
            return False

    def show_logs(self, follow: bool = False, tail: int = 50) -> None:
        """Show container logs"""
        print(f"📋 Showing logs for: {self.container_name}")

        cmd = ["docker", "logs"]
        if follow:
            cmd.append("-f")
        if tail > 0:
            cmd.extend(["--tail", str(tail)])
        cmd.append(self.container_name)

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"❌ Failed to show logs for container: {self.container_name}")
        except KeyboardInterrupt:
            print("\n👋 Stopped following logs")

    def show_status(self) -> None:
        """Show container status"""
        print(f"📊 Status for container: {self.container_name}")

        # Check if container exists
        exit_code, stdout, _ = self.run_command(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name={self.container_name}",
                "--format",
                "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
            ]
        )

        if exit_code == 0 and stdout.strip():
            print(stdout)
        else:
            print(f"ℹ️  Container not found: {self.container_name}")

    def restart(self, build: bool = False, host_port: Optional[int] = None) -> bool:
        """Restart container (stop, remove, optionally build, start)"""
        print("🔄 Restarting container...")

        # Stop and remove existing container
        self.stop_container()
        self.remove_container()

        # Optionally rebuild image
        if build:
            if not self.build_image():
                return False

        # Start container
        return self.start_container(host_port=host_port)

    def cleanup(self) -> None:
        """Clean up stopped containers and unused images"""
        print("🧹 Cleaning up Docker resources...")

        # Remove stopped containers
        self.run_command(["docker", "container", "prune", "-f"])

        # Remove unused images
        self.run_command(["docker", "image", "prune", "-f"])

        print("✅ Cleanup completed")


def main() -> None:
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Discord Agents Docker Management Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_docker.py build          # Build Docker image
  python start_docker.py start          # Start container
  python start_docker.py restart        # Restart container
  python start_docker.py restart --build # Restart and rebuild
  python start_docker.py logs           # Show logs
  python start_docker.py logs --follow  # Follow logs
  python start_docker.py stop           # Stop container
  python start_docker.py status         # Show status
  python start_docker.py cleanup        # Clean up resources
        """,
    )

    parser.add_argument(
        "action",
        choices=["build", "start", "stop", "restart", "logs", "status", "cleanup"],
        help="Action to perform",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Host port to map to container port 8080 (default: 8080)",
    )

    parser.add_argument(
        "--build",
        "-b",
        action="store_true",
        help="Build image before starting (for restart action)",
    )

    parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow logs output (for logs action)",
    )

    parser.add_argument(
        "--tail",
        "-t",
        type=int,
        default=50,
        help="Number of lines to show from the end of logs (default: 50)",
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run container in foreground (for start action)",
    )

    args = parser.parse_args()

    # Check if in correct directory
    if not Path("Dockerfile").exists():
        print(
            "❌ Please run this script from the project root directory (where Dockerfile is located)"
        )
        sys.exit(1)

    manager = DockerManager()

    # Check Docker availability for most actions
    if args.action != "cleanup" and not manager.check_docker():
        sys.exit(1)

    try:
        if args.action == "build":
            success = manager.build_image()

        elif args.action == "start":
            success = manager.start_container(
                detached=not args.foreground, host_port=args.port
            )

        elif args.action == "stop":
            success = manager.stop_container()

        elif args.action == "restart":
            success = manager.restart(build=args.build, host_port=args.port)

        elif args.action == "logs":
            manager.show_logs(follow=args.follow, tail=args.tail)
            success = True

        elif args.action == "status":
            manager.show_status()
            success = True

        elif args.action == "cleanup":
            manager.cleanup()
            success = True

        else:
            print(f"❌ Unknown action: {args.action}")
            success = False

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
