"""
tests/test_scheduler.py - Comprehensive tests for APScheduler service and worker.
Covers start, shutdown, job registration, and lifecycle recreation.
"""
import pytest
from app.services.scheduler_service import SchedulerService
import app.core.config as config_mod


def test_scheduler_lifecycle():
    service = SchedulerService()
    
    # 1. Start with force=True
    started = service.start(force=True)
    assert started is True
    assert service.is_running is True
    
    # 2. Verify job registration
    sched = service._scheduler
    assert sched is not None
    job = sched.get_job("whatsapp_reminder_job")
    assert job is not None
    assert "run_upcoming_appointments_job" in str(job.func)
    
    # 3. Shutdown
    stopped = service.shutdown(wait=False)
    assert stopped is True
    assert service.is_running is False
    
    # 4. Lifecycle recreation (restarting after shutdown must not fail)
    restarted = service.start(force=True)
    assert restarted is True
    assert service.is_running is True
    
    # Final cleanup
    service.shutdown(wait=False)
    assert service.is_running is False


def test_scheduler_respects_flag(monkeypatch):
    service = SchedulerService()
    
    # When ENABLE_SCHEDULER is False and force is False, scheduler must not start
    monkeypatch.setattr(config_mod, "ENABLE_SCHEDULER", False)
    started = service.start(force=False)
    assert started is False
    assert service.is_running is False
