"""
app/workers/scheduler.py - Standalone APScheduler Background Worker.
Can be executed as an independent OS process or container service:
    python -m app.workers.scheduler
This decouples cron and notification dispatch from uvicorn web servers to prevent duplicate jobs.
"""
import sys
import time
import signal
import logging
from app.services.scheduler_service import scheduler_service
from app.core.logging import scheduler_logger

logger = scheduler_logger

running = True

def handle_signal(sig, frame):
    global running
    logger.info(f"Señal {sig} recibida. Deteniendo scheduler worker...")
    running = False
    scheduler_service.shutdown(wait=True)
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Iniciando Worker Autónomo de Scheduler (HiddenSYNC / Turnero)...")
    success = scheduler_service.start(force=True)
    if not success:
        logger.error("No se pudo iniciar el scheduler worker. Verifique la instalación de apscheduler.")
        sys.exit(1)

    logger.info("Worker de Scheduler en ejecución continua. Presione Ctrl+C para finalizar.")
    while running:
        time.sleep(1)

if __name__ == "__main__":
    main()
