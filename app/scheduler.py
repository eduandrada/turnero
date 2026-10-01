"""
app/scheduler.py - Backward compatibility facade for background scheduling and reminders.
Delegates to app.services.scheduler_service.SchedulerService.
"""
from app.services.scheduler_service import (
    scheduler_service,
    SchedulerService,
)

def is_scheduler_running() -> bool:
    return scheduler_service.is_running

def start_scheduler():
    scheduler_service.start(force=True)

def shutdown_scheduler():
    scheduler_service.shutdown(wait=False)

async def check_upcoming_appointments():
    return await scheduler_service.check_upcoming_appointments()

def run_upcoming_appointments_job():
    scheduler_service.run_upcoming_appointments_job()

__all__ = [
    "scheduler_service",
    "SchedulerService",
    "is_scheduler_running",
    "start_scheduler",
    "shutdown_scheduler",
    "check_upcoming_appointments",
    "run_upcoming_appointments_job",
]
