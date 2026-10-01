"""
app/services/live_queue_service.py - Real-time Queue, TV Signage and Walk-in Management.
Calculates who is currently in chair (EN SILLÓN), who is next up, upcoming and completed turns,
along with voice synthesis announcements and display chime triggers.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Appointment, Barber, AuditLog, AppointmentHistory
from app.core.database import get_argentina_now
from app.settings_helper import get_setting, set_setting, DEFAULT_SETTINGS
from app.utils import build_speech_announcement


class LiveQueueService:
    """Encapsulates state management for in-salon TV displays and live queue."""

    @staticmethod
    def get_live_agenda(
        db: Session,
        barber_id: Optional[int] = None,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calcula el estado en vivo de la sala de espera para la pantalla TV o panel de staff."""
        now_dt = get_argentina_now()
        if target_date:
            try:
                curr_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                curr_date = now_dt.date()
        else:
            curr_date = now_dt.date()

        start_day = datetime.combine(curr_date, datetime.min.time())
        end_day = datetime.combine(curr_date, datetime.max.time())

        query = db.query(Appointment).filter(
            Appointment.appointment_time >= start_day,
            Appointment.appointment_time <= end_day,
            Appointment.canceled == False,
            Appointment.status != "CANCELADO"
        )
        if barber_id:
            query = query.filter(Appointment.barber_id == barber_id)

        appts = query.order_by(Appointment.appointment_time.asc()).all()
        now_naive = now_dt.replace(tzinfo=None) if curr_date == now_dt.date() else datetime.combine(curr_date, datetime.min.time())

        in_service_list = []
        next_up_list = []
        upcoming_list = []
        completed_list = []

        for a in appts:
            start_t = a.appointment_time
            dur = a.duration_min or 45
            end_t = a.end_time or (start_t + timedelta(minutes=dur))

            progress_pct = 0
            if start_t <= now_naive <= end_t and (end_t > start_t):
                total_sec = (end_t - start_t).total_seconds()
                elapsed_sec = (now_naive - start_t).total_seconds()
                progress_pct = min(100, max(0, int((elapsed_sec / total_sec) * 100)))

            item = {
                "id": a.id,
                "client_name": a.client_name,
                "barber_id": a.barber_id,
                "barber_name": a.barber_name or "General",
                "service": a.service or "Corte de Autor",
                "duration_min": dur,
                "appointment_time": start_t.isoformat(),
                "time_str": start_t.strftime("%H:%M"),
                "end_time_str": end_t.strftime("%H:%M"),
                "status": a.status,
                "is_now": False,
                "progress_pct": progress_pct,
                "is_checked_in": bool(getattr(a, "is_checked_in", False)),
                "checked_in_at": a.checked_in_at.strftime("%H:%M") if getattr(a, "checked_in_at", None) else None
            }

            st_upper = (a.status or "").upper()
            if st_upper in ["COMPLETADO", "ATENDIDO", "FINALIZADO"]:
                item["status"] = "COMPLETADO"
                completed_list.append(item)
            elif st_upper in ["EN_SILLA", "EN_ATENCION", "EN_SILLON", "ATENDIENDO", "LLAMANDO"]:
                item["is_now"] = True
                item["status"] = "EN SILLÓN"
                in_service_list.append(item)
            else:
                upcoming_list.append(item)

        # Ordenar lista de espera: primero los que ya están físicamente en la sala de espera (is_checked_in), luego por horario
        upcoming_list.sort(key=lambda x: (not x.get("is_checked_in", False), x.get("appointment_time", "")))

        if upcoming_list:
            next_up_list.append(upcoming_list[0])

        barbers = db.query(Barber).filter(Barber.is_active == True).order_by(Barber.display_order.asc()).all()
        barbers_data = [{"id": b.id, "name": b.name, "avatar_url": b.avatar_url, "specialties": b.specialties} for b in barbers]
        b_name = get_setting(db, "barber_name", "BARBERÍA")

        tv_title = get_setting(db, "live_tv_title", "SALA DE ESPERA // TURNERO EN VIVO")
        tv_subtitle = get_setting(db, "live_tv_subtitle", "ATENCIÓN POR SILLÓN")
        tv_marquee = get_setting(db, "live_tv_marquee", "💈 Bienvenido • Turnos en Tiempo Real • Wi-Fi Disponible • Shop Barber")
        voice_enabled = get_setting(db, "live_voice_enabled", "true") == "true"
        chime_enabled = get_setting(db, "live_chime_enabled", "true") == "true"
        auto_refresh_sec = int(get_setting(db, "live_auto_refresh_sec", "10") or 10)
        current_called_id_str = get_setting(db, "live_current_called_id", "")

        called_appointment = None
        if current_called_id_str and current_called_id_str.isdigit():
            c_appt = db.query(Appointment).filter(Appointment.id == int(current_called_id_str)).first()
            if c_appt:
                turn_code = f"T-{c_appt.id:03d}" if c_appt.id < 1000 else f"T-{c_appt.id}"
                speech_text = build_speech_announcement(
                    style=get_setting(db, "voice_communication_style", "moderno"),
                    turn_code=turn_code,
                    client_name=c_appt.client_name,
                    barber_name=c_appt.barber_name or "General",
                    station_name=f"Sillón {c_appt.barber_id or 1}",
                    service_name=c_appt.service or "Corte",
                    custom_template=get_setting(db, "voice_custom_template", "")
                )
                called_appointment = {
                    "id": c_appt.id,
                    "turn_code": turn_code,
                    "client_name": c_appt.client_name,
                    "barber_name": c_appt.barber_name or "General",
                    "service": c_appt.service or "Corte",
                    "time_str": c_appt.appointment_time.strftime("%H:%M"),
                    "speech_text": speech_text
                }

        return {
            "server_time": now_dt.strftime("%H:%M:%S"),
            "server_date": curr_date.strftime("%Y-%m-%d"),
            "barber_name": b_name,
            "tv_title": tv_title,
            "tv_subtitle": tv_subtitle,
            "tv_marquee": tv_marquee,
            "voice_enabled": voice_enabled,
            "chime_enabled": chime_enabled,
            "auto_refresh_sec": auto_refresh_sec,
            "called_appointment": called_appointment,
            "total_today": len(appts),
            "in_service": in_service_list,
            "next_up": next_up_list,
            "upcoming": upcoming_list,
            "completed": completed_list,
            "barbers": barbers_data
        }

    @staticmethod
    def call_appointment(db: Session, appointment_id: int, actor_name: str = "Encargado / Admin") -> Dict[str, Any]:
        """Marca un turno como LLAMANDO y actualiza el anuncio de voz y display."""
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Turno no encontrado.")
        appt.status = "LLAMANDO"
        set_setting(db, "live_current_called_id", str(appt.id))
        db.commit()

        db.add(AppointmentHistory(
            appointment_id=appt.id,
            old_status="CONFIRMADO",
            new_status="LLAMANDO",
            changed_by=actor_name,
            change_reason="Llamado a pantalla TV desde Live Agenda"
        ))
        db.add(AuditLog(
            user_name=actor_name,
            actor=actor_name,
            module="Live Agenda",
            action="Llamar Turno a Pantalla TV",
            description=f"Llamado a pantalla: Turno #{appt.id} ({appt.client_name})",
            record_id=str(appt.id)
        ))
        db.commit()

        turn_code = f"T-{appt.id:03d}" if appt.id < 1000 else f"T-{appt.id}"
        speech_text = build_speech_announcement(
            style=get_setting(db, "voice_communication_style", "moderno"),
            turn_code=turn_code,
            client_name=appt.client_name,
            barber_name=appt.barber_name or "General",
            station_name=f"Sillón {appt.barber_id or 1}",
            service_name=appt.service or "Corte",
            custom_template=get_setting(db, "voice_custom_template", "")
        )

        return {
            "message": f"Turno {turn_code} llamado a pantalla.",
            "turn_code": turn_code,
            "speech_text": speech_text
        }

    @staticmethod
    def create_walk_in(db: Session, data: Dict[str, Any], actor_name: str = "Encargado") -> Dict[str, Any]:
        """Agrega un cliente espontáneo a la cola del día en vivo."""
        name = str(data.get("client_name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="El nombre del cliente es obligatorio.")
        phone = str(data.get("client_phone", "")).strip() or "5493834000000"
        barber_id = data.get("barber_id")
        barber_name = "General"
        if barber_id:
            b = db.query(Barber).filter(Barber.id == barber_id).first()
            if b:
                barber_name = b.name
        service_name = data.get("service_name") or "Corte Espontáneo / En Espera"
        dur = int(data.get("duration_min") or 30)

        now_arg = get_argentina_now().replace(tzinfo=None)

        new_appt = Appointment(
            client_name=name,
            client_phone=phone,
            barber_id=barber_id,
            barber_name=barber_name,
            service=service_name,
            appointment_time=now_arg,
            end_time=now_arg + timedelta(minutes=dur),
            duration_min=dur,
            status="PENDIENTE",
            confirmed=True
        )
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)

        db.add(AuditLog(
            user_name=actor_name,
            actor=actor_name,
            module="Live Agenda",
            action="Walk-in Agregado",
            description=f"Cliente espontáneo: {name} ({service_name}) - Barbero: {barber_name}",
            record_id=str(new_appt.id)
        ))
        db.commit()

        return {"message": "Cliente agregado a la cola en vivo exitosamente.", "appointment_id": new_appt.id}

    @staticmethod
    def finish_and_next(
        db: Session,
        appointment_id: Optional[int] = None,
        barber_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        tip_amount: float = 0.0,
        actor_name: str = "Barbero / Encargado"
    ) -> Dict[str, Any]:
        """
        Cierre ágil de corte ("Sigue el Próximo"):
        1. Finaliza el corte actual (lo pasa a COMPLETADO y acredita puntos Barber Club).
        2. Busca automáticamente al siguiente cliente en cola para ese barbero (o general).
        3. Lo pasa a EN SILLÓN y gatilla el llamado por pantalla TV / Voz fonética.
        """
        now_dt = get_argentina_now()
        start_day = datetime.combine(now_dt.date(), datetime.min.time())
        end_day = datetime.combine(now_dt.date(), datetime.max.time())

        # 1. Identificar el turno actual a finalizar
        curr_appt = None
        if appointment_id:
            curr_appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        else:
            query = db.query(Appointment).filter(
                Appointment.appointment_time >= start_day,
                Appointment.appointment_time <= end_day,
                Appointment.canceled == False,
                Appointment.status.in_(["EN_SILLA", "EN_ATENCION", "LLAMANDO"])
            )
            if barber_id:
                query = query.filter(Appointment.barber_id == barber_id)
            curr_appt = query.order_by(Appointment.appointment_time.asc()).first()

        completed_data = None
        target_barber_id = barber_id

        if curr_appt:
            target_barber_id = target_barber_id or curr_appt.barber_id
            old_st = curr_appt.status
            curr_appt.status = "COMPLETADO"
            curr_appt.confirmed = True
            if payment_method:
                curr_appt.payment_method = payment_method
            
            # Barber Club Points
            from app.api.loyalty import credit_client_loyalty_points
            amount = curr_appt.service_price_snapshot or (curr_appt.service_rel.price if curr_appt.service_rel else 0.0)
            if amount > 0 and curr_appt.client_phone:
                credit_client_loyalty_points(
                    db,
                    client_phone=curr_appt.client_phone,
                    amount=amount,
                    reason=f"Corte/Servicio: {curr_appt.service or 'Barbería'}",
                    reference_id=str(curr_appt.id)
                )

            db.commit()

            db.add(AppointmentHistory(
                appointment_id=curr_appt.id,
                previous_status=old_st,
                new_status="COMPLETADO",
                changed_by=actor_name,
                change_reason="Cierre ágil de corte ('Sigue el próximo')"
            ))
            db.add(AuditLog(
                user_name=actor_name,
                actor=actor_name,
                module="Live Agenda",
                action="Cierre de Corte",
                description=f"Corte de {curr_appt.client_name} (Turno #{curr_appt.id}) finalizado con éxito.",
                record_id=str(curr_appt.id)
            ))
            db.commit()

            completed_data = {
                "id": curr_appt.id,
                "client_name": curr_appt.client_name,
                "barber_name": curr_appt.barber_name,
                "service": curr_appt.service
            }

        # 2. Buscar al siguiente cliente en espera
        next_query = db.query(Appointment).filter(
            Appointment.appointment_time >= start_day,
            Appointment.appointment_time <= end_day,
            Appointment.canceled == False,
            Appointment.status.in_(["PENDIENTE", "CONFIRMADO"])
        )
        if target_barber_id:
            next_query = next_query.filter(
                (Appointment.barber_id == target_barber_id) | (Appointment.barber_id == None)
            )

        next_appt = next_query.order_by(Appointment.appointment_time.asc()).first()

        next_data = None
        speech_text = None

        if next_appt:
            next_old_st = next_appt.status
            next_appt.status = "EN_SILLA"
            next_appt.confirmed = True
            set_setting(db, "live_current_called_id", str(next_appt.id))
            db.commit()

            db.add(AppointmentHistory(
                appointment_id=next_appt.id,
                previous_status=next_old_st,
                new_status="EN_SILLA",
                changed_by=actor_name,
                change_reason="Llamado automático al sillón ('Sigue el próximo')"
            ))
            db.add(AuditLog(
                user_name=actor_name,
                actor=actor_name,
                module="Live Agenda",
                action="Pase a Sillón",
                description=f"Turno #{next_appt.id} ({next_appt.client_name}) pasa a EN SILLÓN.",
                record_id=str(next_appt.id)
            ))
            db.commit()

            turn_code = f"T-{next_appt.id:03d}" if next_appt.id < 1000 else f"T-{next_appt.id}"
            speech_text = build_speech_announcement(
                style=get_setting(db, "voice_communication_style", "moderno"),
                turn_code=turn_code,
                client_name=next_appt.client_name,
                barber_name=next_appt.barber_name or "General",
                station_name=f"Sillón {next_appt.barber_id or 1}",
                service_name=next_appt.service or "Corte",
                custom_template=get_setting(db, "voice_custom_template", "")
            )

            next_data = {
                "id": next_appt.id,
                "turn_code": turn_code,
                "client_name": next_appt.client_name,
                "barber_name": next_appt.barber_name or "General",
                "service": next_appt.service or "Corte",
                "time_str": next_appt.appointment_time.strftime("%H:%M"),
                "speech_text": speech_text
            }

        msg = "Corte finalizado."
        if completed_data and next_data:
            msg = f"Corte de {completed_data['client_name']} finalizado. ¡Sigue {next_data['client_name']} en el sillón!"
        elif completed_data:
            msg = f"Corte de {completed_data['client_name']} finalizado. No hay más turnos pendientes por ahora."
        elif next_data:
            msg = f"¡Sigue {next_data['client_name']} en el sillón!"

        return {
            "status": "success",
            "message": msg,
            "completed_appointment": completed_data,
            "next_appointment": next_data,
            "speech_text": speech_text
        }


live_queue_service = LiveQueueService()

