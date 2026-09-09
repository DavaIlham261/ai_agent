import os
import secrets
import time
from collections import defaultdict

from dotenv import load_dotenv 
from fastapi import Header, HTTPException, Request

load_dotenv()

AGENT_API_KEY = os.getenv("AGENT_API_KEY")
if not AGENT_API_KEY:
    raise RuntimeError("AGENT_API_KEY belum diset di .env")

RATE_LIMIT_MAX_FAILS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

# in-memory sementara sebelum pake redis
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip:str) -> None:
    now = time.time()
    attempts = _failed_attempts[ip]
    attempts[:] = [t for t in attempts if now -t < RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= RATE_LIMIT_MAX_FAILS:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan gagal. Silakan coba lagi nanti."
        )    
        
def _record_failure(ip: str) -> None:
    _failed_attempts[ip].append(time.time())
    
async def verify_api_key(
    request: Request,
    x_api_key: str = Header(default=None),
) -> None:
    client_ip = request.client.host if request.client else 'unknows'
    _check_rate_limit(client_ip)
    
    # secrets.compare_digest wajib (SKPL-NF04) — mencegah timing attack.
    # Guard `x_api_key is None` diletakkan sebelum compare_digest via short-circuit `or`,
    # supaya tidak crash TypeError kalau header memang tidak dikirim.
    if x_api_key is None or not secrets.compare_digest(x_api_key, AGENT_API_KEY):
        _record_failure(client_ip)
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

    return True