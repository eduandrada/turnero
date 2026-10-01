"""
app/services/scheduler_service.py - Scheduler service for automated background reminders and cron tasks.
Manages APScheduler lifecycle with graceful recreation after shutdown, safe execution, and worker decoupling.
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core import config
from app.core.database import SessionLocal, get_argentina_now
from app.core.logging import scheduler_logger
from app.models import Appointment

logger = scheduler_logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None
    logger.warning("apscheduler no está instalado. El planificador estará en modo manual.")


class SchedulerService:
    """Manages APScheduler background scheduler instance, jobs, and lifecycle."""

    def __init__(self):
        self._scheduler: Optional[BackgroundScheduler] = None

    def _get_or_create_scheduler(self) -> Optional[BackgroundScheduler]:
        if BackgroundScheduler is None:
            return None
        # Si no existe o fue apagado previamente, creamos una nueva instancia limpia
        if self._scheduler is None or not hasattr(self._scheduler, "running") or self._scheduler.state == 0:
            self._scheduler = BackgroundScheduler()
        return self._scheduler

    @property
    def is_running(self) -> bool:
        """Indica si el planificador está activo y ejecutando tareas."""
        return bool(self._scheduler and getattr(self._scheduler, "running", False))

    def start(self, force: bool = False) -> bool:
        """
        Inicializa el planificador en background y programa las tareas periódicas.
        Respeta la variable ENABLE_SCHEDULER a menos que se fuerce explícitamente.
        """
        if not config.ENABLE_SCHEDULER and not force:
            logger.info("SchedulerService: Inicio omitido porque ENABLE_SCHEDULER=false (modo worker separado).")
            return False

        sched = self._get_or_create_scheduler()
        if sched is None:
            logger.warning("SchedulerService: APScheduler no disponible.")
            return False

        try:
            if not sched.running:
                # Si la instancia fue previamente finalizada (state==2/stopped), recrear
                if getattr(sched, "state", 0) == 2:
                    self._scheduler = BackgroundScheduler()
                    sched = self._scheduler

                sched.add_job(
                    self.run_upcoming_appointments_job,
                    "interval",
                    minutes=5,
                    id="whatsapp_reminder_job",
                    replace_existing=True
                )
                sched.start()
                logger.info("SchedulerService: BackgroundScheduler iniciado (intervalo: 5 min).")
                return True
            return True
        except Exception as e:
            logger.error(f"SchedulerService: Error al iniciar APScheduler: {e}")
            return False

    def shutdown(self, wait: bool = False) -> bool:
        """Detiene el planificador si está activo."""
        if self._scheduler is not None:
            try:
                if self._scheduler.running:
                    self._scheduler.shutdown(wait=wait)
                    logger.info("SchedulerService: BackgroundScheduler detenido formalmente.")
                return True
            except Exception as e:
                logger.error(f"SchedulerService: Error al apagar APScheduler: {e}")
                return False
            finally:
                self._scheduler = None
        return True

    async def check_upcoming_appointments(self) -> int:
        """
        Busca citas programadas entre [now] y [now + 2h] que aún no hayan recibido recordatorio
        y dispara las notificaciones interactivas de WhatsApp.
        """
        from app.services.whatsapp_service import send_whatsapp_interactive_reminder

        logger.info("SchedulerService: Verificando citas próximas para envío de recordatorios...")
        db: Session = SessionLocal()
        sent_count = 0
        try:
            now = get_argentina_now().replace(tzinfo=None)
            window_end = now + timedelta(hours=2, minutes=5)

            appointments = db.query(Appointment).filter(
                Appointment.appointment_time >= now,
                Appointment.appointment_time <= window_end,
                Appointment.reminder_sent == False,
                Appointment.canceled == False
            ).all()

            for appt in appointments:
                service_title = appt.service or (appt.service_rel.name if appt.service_rel else "Servicio de Barbería")
                try:
                    success = await send_whatsapp_interactive_reminder(
                        phone=appt.client_phone,
                        appointment_id=appt.id,
                        client_name=appt.client_name,
                        service=service_title,
                        app_time=appt.appointment_time
                    )
                    if success:
                        appt.reminder_sent = True
                        db.commit()
                        sent_count += 1
                except Exception as ex:
                    logger.error(f"SchedulerService: Error enviando recordatorio para turno #{appt.id}: {ex}")
            return sent_count
        except Exception as e:
            logger.exception(f"SchedulerService: Error en check_upcoming_appointments: {e}")
            return 0
        finally:
            db.close()

    def run_upcoming_appointments_job(self) -> None:
        """Ejecuta recordatorios de WhatsApp y PWA Push sincrónicamente dentro del job de APScheduler."""
        from app.api.push import check_and_send_push_reminders
        try:
            asyncio.run(self.check_upcoming_appointments())
        except Exception as e:
            logger.exception(f"SchedulerService: Excepción en cron job de recordatorios WhatsApp: {e}")

        try:
            db = SessionLocal()
            try:
                check_and_send_push_reminders(db)
            finally:
                db.close()
        except Exception as e:
            logger.exception(f"SchedulerService: Excepción en cron job de notificaciones Push PWA: {e}")



# Instancia singleton predeterminada
scheduler_service = SchedulerService()
