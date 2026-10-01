"""
app/availability_engine.py - Backward compatibility facade.
Re-exports slot availability functions from app.services.availability_service.
"""
from app.services.availability_service import (
    DEFAULT_SLOT_INTERVAL_MIN,
    parse_time_str,
    time_to_minutes,
    minutes_to_time,
    get_barber_working_windows,
    get_schedule_blocks,
    get_schedule_exceptions_for_date,
    is_day_blocked_for_barber,
    calculate_available_slots,
    availability_service,
    AvailabilityService,
)

__all__ = [
    "DEFAULT_SLOT_INTERVAL_MIN",
    "parse_time_str",
    "time_to_minutes",
    "minutes_to_time",
    "get_barber_working_windows",
    "get_schedule_blocks",
    "get_schedule_exceptions_for_date",
    "is_day_blocked_for_barber",
    "calculate_available_slots",
    "availability_service",
    "AvailabilityService",
]
