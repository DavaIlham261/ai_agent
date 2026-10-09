import os
import threading
import yaml

PROJECTS_FILE = os.getenv("PROJECTS_FILE", "projects.yaml")
_lock = threading.Lock()

def load_projects() -> dict:
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("projects", {})


PROJECTS = load_projects()


def get_project(project_id: str) -> dict | None:
    return PROJECTS.get(project_id)


def register_project(project_id: str, tailscale_ip: str, port: int, root_path: str = "/app/workspace") -> None:
    with _lock:
        PROJECTS[project_id] = {"tailscale_ip": tailscale_ip, "port": port, "root_path": root_path}
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump({"projects": PROJECTS}, f, allow_unicode=True, sort_keys=False)