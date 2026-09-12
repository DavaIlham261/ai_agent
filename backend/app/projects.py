import os
import yaml

PROJECTS_FILE = os.getenv("PROJECTS_FILE", "projects.yaml")
print("PROJEECT_FILES:", PROJECTS_FILE)

def load_projects() -> dict:
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("projects", {})


PROJECTS = load_projects()


def get_project(project_id: str) -> dict | None:
    return PROJECTS.get(project_id)