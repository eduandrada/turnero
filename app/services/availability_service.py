"""
app/services/availability_service.py - Motor de Disponibilidad y Gestión de Turnos Configurable
HiddenSYNC AI 2026

Calcula dinámicamente los slots libres mediante operaciones de intervalos temporales:
RangoOperativo - Pausas - Bloqueos/Feriados - ReservasConfirmadas (con buffers de servicio).
No pre-genera slots estáticos en base de datos.
"""
import json
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import Barber, Service, Appointment, BarberSchedule, ScheduleException
from app.core.database import get_argentina_now
from app.settings_helper import get_setting

DEFAULT_SLOT_INTERVAL_MIN = 15

def parse_time_str(t_str: str) -> Optional[time]:
    """Parsea una cadena 'HH:MM' a objeto time."""
    if not t_str:
        return None
    try:
        parts = t_str.strip().split(":")
        return time(hour=int(parts[0]), minute=int(parts[1]))
    except Exception:
        return None

def time_to_minutes(t: time) -> int:
    """Convierte time a minutos desde la medianoche."""
    return t.hour * 60 + t.minute

def minutes_to_time(m: int) -> time:
    """Convierte minutos desde la medianoche a objeto time."""
    return time(hour=m // 60, minute=m % 60)

def get_barber_working_windows(
    db: Session,
    barber_id: int,
    target_date: date
) -> List[Tuple[time, time]]:
    """
    Obtiene las ventanas de trabajo del barbero para una fecha específica (día de la semana 0..6).
    Si no tiene BarberSchedule personalizado, utiliza la configuración global de business_hours o settings.
    """
    weekday = target_date.weekday() # 0 = Lunes, 6 = Domingo

    schedule = db.query(BarberSchedule).filter(
        BarberSchedule.barber_id == barber_id,
        BarberSchedule.day_of_week == weekday
    ).first()

    if schedule:
        if not schedule.is_working:
            return []
        windows = []
        t1_start = parse_time_str(schedule.start_time_1)
        t1_end = parse_time_str(schedule.end_time_1)
        if t1_start and t1_end:
            windows.append((t1_start, t1_end))

        if schedule.start_time_2 and schedule.end_time_2:
            t2_start = parse_time_str(schedule.start_time_2)
            t2_end = parse_time_str(schedule.end_time_2)
            if t2_start and t2_end:
                windows.append((t2_start, t2_end))
        return windows

    # Fallback: Revisar si la barbería tiene business_hours configurados
    bh_json = get_setting(db, "business_hours", "{}")
    try:
        bh_config = json.loads(bh_json)
    except Exception:
        bh_config = {}

    days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    day_name = days_es[weekday]

    if day_name in bh_config:
        day_setting = bh_config[day_name]
        if not day_setting.get("active", True):
            return []
        open_t = parse_time_str(day_setting.get("open", "09:00")) or time(9, 0)
        close_t = parse_time_str(day_setting.get("close", "20:00")) or time(20, 0)
        pause_start_str = day_setting.get("pause_start", "")
        pause_end_str = day_setting.get("pause_end", "")
        if pause_start_str and pause_end_str:
            p_start = parse_time_str(pause_start_str)
            p_end = parse_time_str(pause_end_str)
            if p_start and p_end and time_to_minutes(p_start) < time_to_minutes(p_end):
                return [(open_t, p_start), (p_end, close_t)]
        return [(open_t, close_t)]

    if weekday == 6: # Domingo cerrado por defecto
        return []

    # Configuración por defecto si no hay business_hours
    open_time_str = get_setting(db, "open_time", "09:00")
    close_time_str = get_setting(db, "close_time", "21:00")
    pause_start_str = get_setting(db, "pause_start", "")
    pause_end_str = get_setting(db, "pause_end", "")

    t_open = parse_time_str(open_time_str) or time(9, 0)
    t_close = parse_time_str(close_time_str) or time(21, 0)
    t_p_start = parse_time_str(pause_start_str) if pause_start_str else None
    t_p_end = parse_time_str(pause_end_str) if pause_end_str else None

    if t_p_start and t_p_end and time_to_minutes(t_p_start) < time_to_minutes(t_p_end):
        return [(t_open, t_p_start), (t_p_end, t_close)]

    return [(t_open, t_close)]

def get_schedule_blocks(
    db: Session,
    barber_id: int,
    date_str: str
) -> List[Tuple[Optional[time], Optional[time]]]:
    """Obtiene bloqueos manuales, feriados y licencias para la fecha dada (globales o específicos del barbero)."""
    exceptions = db.query(ScheduleException).filter(
        ScheduleException.date == date_str,
        or_(
            ScheduleException.barber_id == barber_id,
            ScheduleException.barber_id.is_(None)
        )
    ).all()

    blocks = []
    for exc in exceptions:
        t_start = parse_time_str(exc.start_time)
        t_end = parse_time_str(exc.end_time)
        blocks.append((t_start, t_end))
    return blocks

get_schedule_exceptions_for_date = get_schedule_blocks

def is_day_blocked_for_barber(db: Session, barber_id: int, date_str: str) -> bool:
    """Retorna True si toda la jornada está bloqueada para el barbero o a nivel global."""
    blocks = get_schedule_blocks(db, barber_id, date_str)
    for b_start, b_end in blocks:
        if b_start is None and b_end is None:
            return True
    return False

def calculate_available_slots(
    db: Session,
    target_date_str: str,
    barber_id: int,
    service_id: Optional[int] = None,
    duration_min: Optional[int] = None,
    allow_overbooking: bool = False
) -> Dict[str, Any]:
    """
    Calcula dinámicamente los horarios disponibles para un barbero y servicio en una fecha dada.
    Considera:
      - Rango laboral y pausas del barbero (BarberSchedule).
      - Bloqueos manuales y feriados (ScheduleException).
      - Reservas existentes y sus buffers de preparación y limpieza.
      - Antelación mínima (min_advance_hours).
      - Duración acumulada de servicio base + agregados opcionales.
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "Formato de fecha inválido. Usar YYYY-MM-DD.", "slots": []}

    now_catamarca = get_argentina_now()
    today_catamarca = now_catamarca.date()

    # 1. Ventana máxima a futuro (e.g. 30 días)
    max_days = int(get_setting(db, "max_future_booking_days", "30") or 30)
    if (target_date - today_catamarca).days > max_days:
        return {"slots": [], "reason": f"Solo se permite reservar con hasta {max_days} días de antelación."}

    if target_date < today_catamarca:
        return {"slots": [], "reason": "No es posible reservar en fechas pasadas."}

    # 2. Obtener duración del servicio y buffers
    service_duration = duration_min if (duration_min and duration_min > 0) else 45
    prep_buffer = 0
    clean_buffer = 5
    if service_id:
        srv = db.query(Service).filter(Service.id == service_id).first()
        if srv:
            if not duration_min or duration_min <= 0:
                service_duration = srv.duration_min or 45
            prep_buffer = getattr(srv, "prep_buffer_min", 0) or 0
            clean_buffer = getattr(srv, "clean_buffer_min", 5) or 5

    total_service_block = prep_buffer + service_duration + clean_buffer

    # 3. Ventanas operativas del barbero para ese día
    windows = get_barber_working_windows(db, barber_id, target_date)
    if not windows:
        return {"slots": [], "reason": "El profesional no atiende en el día seleccionado."}

    # 4. Bloqueos manuales y feriados
    blocks = get_schedule_blocks(db, barber_id, target_date_str)
    for b_start, b_end in blocks:
        if b_start is None and b_end is None:
            return {"slots": [], "reason": "Jornada no disponible por feriado, descanso o bloqueo administrativo."}

    # 5. Obtener citas existentes activas del barbero para la fecha
    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)

    existing_appts = db.query(Appointment).filter(
        Appointment.barber_id == barber_id,
        Appointment.appointment_time >= start_of_day,
        Appointment.appointment_time <= end_of_day,
        Appointment.status.notin_(["CANCELADO", "NO_SHOW"])
    ).all()

    # Mapear intervalos ocupados en minutos desde la medianoche
    busy_intervals = []
    for appt in existing_appts:
        appt_start_m = time_to_minutes(appt.appointment_time.time())
        appt_duration = appt.duration_min or 45
        appt_end_m = appt_start_m + appt_duration + clean_buffer
        busy_intervals.append((appt_start_m, appt_end_m, appt.id))

    # Mapear bloques manuales en minutos
    for b_start, b_end in blocks:
        if b_start and b_end:
            busy_intervals.append((time_to_minutes(b_start), time_to_minutes(b_end), -1))

    # 6. Antelación mínima (e.g. 1 hora antes de la cita si es hoy)
    min_advance_min = int(get_setting(db, "min_advance_minutes", "60") or 60)
    current_time_m = time_to_minutes(now_catamarca.time()) if target_date == today_catamarca else -1

    # 7. Generar slots candidatos en pasos de DEFAULT_SLOT_INTERVAL_MIN
    available_slots = []
    slot_step = int(get_setting(db, "slot_interval_minutes", str(DEFAULT_SLOT_INTERVAL_MIN)) or DEFAULT_SLOT_INTERVAL_MIN)

    for w_start, w_end in windows:
        w_start_m = time_to_minutes(w_start)
        w_end_m = time_to_minutes(w_end)

        slot_m = w_start_m
        while slot_m + service_duration <= w_end_m:
            slot_end_m = slot_m + service_duration

            if target_date == today_catamarca and slot_m < current_time_m + min_advance_min:
                slot_m += slot_step
                continue

            has_conflict = False
            for busy_start, busy_end, _ in busy_intervals:
                if slot_m < busy_end and (slot_end_m + clean_buffer) > busy_start:
                    has_conflict = True
                    break

            if not has_conflict or allow_overbooking:
                slot_time_obj = minutes_to_time(slot_m)
                time_str = slot_time_obj.strftime("%H:%M")
                available_slots.append(time_str)

            slot_m += slot_step

    return {
        "date": target_date_str,
        "barber_id": barber_id,
        "service_duration": service_duration,
        "prep_buffer": prep_buffer,
        "clean_buffer": clean_buffer,
        "slots": available_slots,
        "total_available": len(available_slots)
    }

class AvailabilityService:
    @staticmethod
    def get_available_slots(db: Session, date_str: str, barber_id: int, service_id: Optional[int] = None, allow_overbooking: bool = False) -> Dict[str, Any]:
        return calculate_available_slots(db, date_str, barber_id, service_id, allow_overbooking)

    @staticmethod
    def validate_slot(db: Session, date_str: str, time_str: str, barber_id: int, service_id: Optional[int] = None) -> bool:
        res = calculate_available_slots(db, date_str, barber_id, service_id)
        return time_str in res.get("slots", [])

    @staticmethod
    def is_available(db: Session, date_str: str, time_str: str, barber_id: int, service_id: Optional[int] = None) -> bool:
        return AvailabilityService.validate_slot(db, date_str, time_str, barber_id, service_id)

availability_service = AvailabilityService()
