import os
import json
import uuid
import argparse
import requests
import subprocess

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("AGENT_API_KEY")
MCP_IMAGE = "mcp-server-image"
PORTS_REGISTRY = Path(__file__).parent / "ports.json"

if not API_KEY:
    raise RuntimeError("AGENT_API_KEY belum diset di .env")


def find_project_id() -> str:
    """Cari .agent-project.json mulai dari folder saat ini, naik ke folder induk."""
    cwd = Path.cwd()
    for folder in [cwd, *cwd.parents]:
        marker = folder / ".agent-project.json"
        if marker.is_file():
            data = json.loads(marker.read_text(encoding="utf-8"))
            return data["project_id"]
    print(f"[Info] Tidak ada .agent-project.json ditemukan.")
    return None

def get_tailscale_ip() -> str:
    result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def pick_port() -> int:
    used = json.loads(PORTS_REGISTRY.read_text(encoding="utf-8")) if PORTS_REGISTRY.is_file() else {}
    taken = set(used.values())
    port = 8101
    while port in taken:
        port += 1
    return port

def save_port_assignment(project_id: str, port: int) -> None:
    used = json.loads(PORTS_REGISTRY.read_text(encoding="utf-8")) if PORTS_REGISTRY.is_file() else {}
    used[project_id] = port
    PORTS_REGISTRY.write_text(json.dumps(used, indent=2), encoding="utf-8")

def cmd_setup():
    project_path = Path.cwd()
    marker = project_path / ".agent-project.json"
    if marker.is_file():
        print("Folder ini sudah terdaftar. Hapus .agent-project.json dulu kalau mau setup ulang.")
        return

    default_id = project_path.name.lower().replace(" ", "-")
    project_id = input(f"Project ID [{default_id}]: ").strip() or default_id
    port = pick_port()
    print(f"Port dipilih otomatis: {port}")

    print("Menjalankan MCP Server container...")
    subprocess.run(["docker", "rm", "-f", project_id], capture_output=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", project_id,
            "-p", f"{port}:8100",
            "-v", f"{project_path}:/app/workspace",
            "-e", "ROOT_PATH=/app/workspace",
            MCP_IMAGE,
        ],
        check=True,
    )

    print("Mendeteksi IP Tailscale laptop ini...")
    tailscale_ip = get_tailscale_ip()

    print("Mendaftarkan proyek ke backend...")
    resp = requests.post(
        f"{BASE_URL}/api/v1/projects/register",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={"project_id": project_id, "tailscale_ip": tailscale_ip, "port": port, "root_path": "/app/workspace"},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[Gagal mendaftar ke backend]: {resp.text}")
        return

    marker.write_text(json.dumps({"project_id": project_id}, indent=2), encoding="utf-8")
    save_port_assignment(project_id, port)
    print(f"\nSelesai! Jalankan 'agent start' dari folder ini kapan saja.")


def run_chat_loop(project_id: str):
    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    print("=== AI Agent CLI ===")
    print(f"Project: {project_id} | Session: {session_id}")
    print("Ketik 'exit' untuk keluar.\n")

    while True:
        try:
            prompt = input("Kamu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa.")
            break
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit"):
            print("Sampai jumpa.")
            break
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/agent/run",
                headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                json={"prompt": prompt, "session_id": session_id, "project_id": project_id},
                timeout=610,
            )
        except requests.exceptions.Timeout:
            print("[Timeout] Backend tidak merespons dalam waktu wajar.\n")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[Gagal terhubung ke backend]: {e}\n")
            continue
        if response.status_code != 200:
            print(f"[Error {response.status_code}]: {response.json().get('detail', response.text)}\n")
            continue
        data = response.json()
        print(f"\nAgen: {data['response']}")
        if data["execution_steps"]:
            print(f"  (pakai tool {len(data['execution_steps'])}x)")
        print()

def cmd_start():
    project_id = find_project_id()
    if project_id is None:
        print("Folder ini belum terdaftar. Jalankan 'agent setup' dulu.")
        return
    run_chat_loop(project_id)


def main():
    parser = argparse.ArgumentParser(prog="agent")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="Daftarkan folder saat ini sebagai proyek baru")
    sub.add_parser("start", help="Mulai sesi chat untuk proyek di folder saat ini")
    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    else:
        cmd_start()  # tanpa argumen = default ke 'start'


if __name__ == "__main__":
    main()