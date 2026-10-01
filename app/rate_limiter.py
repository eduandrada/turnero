"""
app/rate_limiter.py - Rate Limiter Liviano y Eficiente en Memoria
HiddenSYNC AI 2026

Protege la API contra ataques de fuerza bruta, abuso y scraping:
- /api/admin/login: máximo 6 intentos por minuto por IP.
- /api/appointments: máximo 15 solicitudes por minuto por IP.
- /api/shop/orders: máximo 15 solicitudes por minuto por IP.
Devuelve HTTP 429 con cabecera Retry-After sin bloquear usuarios legítimos.
"""

import time
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException

# Estructura: { "scope:ip": [timestamp_1, timestamp_2, ...] }
_REQUEST_HISTORY: Dict[str, List[float]] = {}
_LAST_CLEANUP: float = time.time()

def check_rate_limit(request: Request, scope: str = "default", max_requests: int = 15, window_seconds: int = 60) -> None:
    """
    Verifica si la IP del cliente ha superado el número de solicitudes permitidas en la ventana de tiempo.
    Lanza HTTPException(429) si se sobrepasa el límite.
    """
    global _LAST_CLEANUP

    # Obtener IP del cliente (considerando proxies/load balancers comunes)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    key = f"{scope}:{client_ip}"
    now = time.time()

    # Limpieza periódica cada 5 minutos de claves antiguas
    if now - _LAST_CLEANUP > 300:
        cutoff = now - 300
        keys_to_del = []
        for k, timestamps in _REQUEST_HISTORY.items():
            _REQUEST_HISTORY[k] = [t for t in timestamps if t > cutoff]
            if not _REQUEST_HISTORY[k]:
                keys_to_del.append(k)
        for k in keys_to_del:
            _REQUEST_HISTORY.pop(k, None)
        _LAST_CLEANUP = now

    timestamps = _REQUEST_HISTORY.get(key, [])
    cutoff = now - window_seconds
    # Filtrar solo marcas de tiempo dentro de la ventana
    valid_timestamps = [t for t in timestamps if t > cutoff]

    if len(valid_timestamps) >= max_requests:
        retry_after = int(window_seconds - (now - valid_timestamps[0]))
        raise HTTPException(
            status_code=429,
            detail="Límite de solicitudes excedido. Por favor intente nuevamente en unos instantes.",
            headers={"Retry-After": str(max(1, retry_after))}
        )

    valid_timestamps.append(now)
    _REQUEST_HISTORY[key] = valid_timestamps
