import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import logging
import subprocess
from datetime import datetime, timezone
import re



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")


ROOT_PATH = Path(os.environ.get("ROOT_PATH", "/app/workspace")).resolve()
MCP_PORT = int(os.environ.get("MCP_PORT", "8100"))

MAX_OUTPUT_CHARS = 5000
COMMAND_TIMEOUT_SECONDS = 30
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/(?:\s|$)",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"rm\s+-rf\s+\.\.",
    r":\(\)\s*\{\s*:\|:&\s*\};:",       # fork bomb
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/(sd|nvme|hd)",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bsudo\b",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"curl[^|]*\|\s*(sh|bash)",
    r"wget[^|]*\|\s*(sh|bash)",
]
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]



mcp = FastMCP("client-mcp-server", host="0.0.0.0", port=MCP_PORT)


def resolve_safe_path(relative_path: str) -> Path:
    """SKPL-NF05: resolve ke absolute path, tolak kalau keluar dari ROOT_PATH
    (termasuk lewat symlink, karena .resolve() mengikuti symlink sampai path aslinya)."""
    candidate = (ROOT_PATH / relative_path).resolve()
    if not candidate.is_relative_to(ROOT_PATH):
        raise ValueError(f"Path di luar root yang diizinkan: {relative_path}")
    return candidate


def _run_git(*args) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT_PATH,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, (result.stdout + result.stderr)
    except Exception as e:
        return False, str(e)


def _ensure_git_repo() -> None:
    if not (ROOT_PATH / ".git").exists():
        ok, msg = _run_git("init")
        if not ok:
            logger.warning("git init gagal: %s", msg)
            return
        _run_git("config", "user.email", "agent@localhost")
        _run_git("config", "user.name", "AI Agent")


def _auto_commit(message: str) -> None:
    """Kegagalan commit TIDAK boleh menggagalkan operasi file (SKPL-F06) — hanya dicatat di log."""
    _ensure_git_repo()
    ok_add, msg_add = _run_git("add", "-A")
    if not ok_add:
        logger.warning("git add gagal: %s", msg_add)
        return
    ok_commit, msg_commit = _run_git("commit", "-m", message, "--allow-empty")
    if not ok_commit:
        logger.warning("git commit gagal: %s", msg_commit)


def _is_dangerous(command: str) -> str | None:
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None



TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".json", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".html", ".css", ".sh",
}


@mcp.tool()
def list_directory(path: str = ".") -> list[str]:
    """Melihat struktur folder dan file di dalam workspace."""
    target = resolve_safe_path(path)
    if not target.is_dir():
        raise ValueError(f"Bukan direktori: {path}")
    return sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())


@mcp.tool()
def read_file(filepath: str) -> str:
    """Membaca isi file teks/kode. File biner atau di luar workspace ditolak."""
    target = resolve_safe_path(filepath)
    if not target.is_file():
        raise ValueError(f"File tidak ditemukan: {filepath}")
    if target.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError(f"Ekstensi tidak diizinkan (kemungkinan file biner): {target.suffix}")
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"File tidak bisa dibaca sebagai teks: {filepath}")


@mcp.tool()
def write_file(filepath: str, content: str, session_id: str = "unknown") -> str:
    """Menulis file baru atau menimpa seluruh isi file lama."""
    target = resolve_safe_path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    _auto_commit(f"pre-agent-edit: {datetime.now(timezone.utc).isoformat()}")

    target.write_text(content, encoding="utf-8")

    _auto_commit(f"agent-edit: write_file {filepath} [session:{session_id}]")

    return f"File berhasil ditulis: {filepath}"


@mcp.tool()
def patch_file(
    filepath: str, search_text: str, replace_text: str, session_id: str = "unknown"
) -> str:
    """Mengubah bagian spesifik file (mengganti kemunculan search_text yang unik dengan replace_text)."""
    target = resolve_safe_path(filepath)
    if not target.is_file():
        raise ValueError(f"File tidak ditemukan: {filepath}")

    original = target.read_text(encoding="utf-8")
    occurrences = original.count(search_text)
    if occurrences == 0:
        raise ValueError(f"search_text tidak ditemukan di file: {filepath}")
    if occurrences > 1:
        raise ValueError(
            f"search_text ditemukan {occurrences} kali (harus unik) di file: {filepath}"
        )

    _auto_commit(f"pre-agent-edit: {datetime.now(timezone.utc).isoformat()}")

    updated = original.replace(search_text, replace_text, 1)
    target.write_text(updated, encoding="utf-8")

    _auto_commit(f"agent-edit: patch_file {filepath} [session:{session_id}]")

    return f"File berhasil di-patch: {filepath}"

@mcp.tool()
def execute_bash(command: str) -> str:
    """Menjalankan perintah shell di dalam workspace untuk keperluan testing (mis. python script.py)."""
    blocked_by = _is_dangerous(command)
    if blocked_by:
        raise ValueError(
            f"Perintah diblokir karena berpotensi berbahaya (cocok pola: {blocked_by})"
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ROOT_PATH,
            stdin=subprocess.DEVNULL,   # cegah perintah menggantung nunggu input manual
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise ValueError(
            f"Perintah melebihi batas waktu {COMMAND_TIMEOUT_SECONDS} detik dan dihentikan."
        )

    output = result.stdout + result.stderr
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[output dipotong]..."

    return f"exit_code={result.returncode}\n{output}"

@mcp.tool()
def append_file(filepath: str, content: str, session_id: str = "unknown") -> str:
    """Menambahkan konten ke akhir file (otomatis membuat file baru kalau belum ada).
    Cocok untuk menulis file panjang secara bertahap lewat beberapa panggilan tool
    berurutan, supaya tidak terbentur batas token dalam satu kali generate."""
    target = resolve_safe_path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    _auto_commit(f"pre-agent-edit: {datetime.now(timezone.utc).isoformat()}")

    with target.open("a", encoding="utf-8") as f:
        f.write(content)

    new_size = target.stat().st_size
    _auto_commit(f"agent-edit: append_file {filepath} [session:{session_id}]")

    return f"Konten ditambahkan ke {filepath}. Ukuran file sekarang: {new_size} bytes."

@mcp.tool()
def validate_file(filepath: str):
    """Mengecek syntax dasar file HTML/CSS/JS, melaporkan error kalau ada.
    Pakai ini SETELAH menulis file, sebelum mengklaim file sudah benar."""
    target = resolve_safe_path(filepath)
    if not target.is_file():
        raise ValueError(f"File tidak ditemukan: {filepath}")

    content = target.read_text(encoding="utf-8")
    ext = target.suffix.lower()

    if ext == ".css":
        import tinycss2
        rules = tinycss2.parse_stylesheet(content, skip_whitespace=True, skip_comments=True)
        errors = [
            f"Baris {r.source_line}: {r.message}"
            for r in rules if r.type == "error"
        ]
        if errors:
            return "CSS INVALID:\n" + "\n".join(errors)
        return "CSS valid, tidak ada error syntax."

    if ext == ".html":
        import html5lib
        try:
            html5lib.parse(content)
        except Exception as e:
            return f"HTML INVALID: {e}"
        return "HTML valid (bisa di-parse tanpa error fatal)."

    if ext == ".js":
        import esprima
        try:
            esprima.parseScript(content)
        except Exception as e:
            return f"JS INVALID: {e}"
        return "JS valid, tidak ada error syntax."

    return f"Validasi tidak didukung untuk ekstensi {ext} (cuma .html/.css/.js)."
    

if __name__ == "__main__":
    mcp.run(transport="streamable-http")