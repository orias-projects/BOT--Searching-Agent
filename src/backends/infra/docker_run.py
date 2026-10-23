"""
Docker helper: ensure Docker is running, start Desktop if needed, wait for server.
"""
import subprocess
import sys
import time
from pathlib import Path

import requests


def isDockerRunning() -> bool:
    try:
        out = subprocess.check_output(
            "docker info", shell=True, stderr=subprocess.STDOUT
        )
        return b"Server Version" in out
    except Exception:
        return False


def startDocker(dockerPath: str) -> None:
    print("🚀 Starting Docker Desktop...")
    if not Path(dockerPath).exists():
        print("❌ Docker Desktop not found!")
        sys.exit(1)
    subprocess.Popen(f'"{dockerPath}"')
    time.sleep(5)


def dockerEnsure(dockerPath: str) -> None:
    if not isDockerRunning():
        startDocker(dockerPath)
        while not isDockerRunning():
            print("⏳ Waiting for Docker to start...")
            time.sleep(5)
    else:
        print("✅ Docker is ready")


def serverWait(url: str, successMsg: str, timeout: int = 60) -> None:
    startTime = time.time()
    while time.time() - startTime < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(successMsg)
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    raise RuntimeError("Server failed to start")
