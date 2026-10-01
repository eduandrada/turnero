"""
app/api/admin/settings.py - Endpoints de Configuración, Multimedia, Identidad, Logs y Auditoría
HiddenSYNC AI 2026
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db, get_argentina_now
from app.models import AdminUser, AuditLog, NotificationLog
from app.schemas import BulkSettingsUpdate, AuditLogRead, NotificationLogRead
from app.core.dependencies import get_current_admin, require_admin_role, require_encargado_or_admin
from app.settings_helper import get_all_settings, get_setting, set_setting, bulk_set_settings
from app.image_service import process_and_save_image, delete_orphan_file, ImageProcessingError, UPLOAD_BASE_DIR

logger = logging.getLogger("hiddensync.admin.settings")

router = APIRouter(tags=["Admin Settings & System"])

UPLOADS_DIR = UPLOAD_BASE_DIR
STATIC_DIR = os.path.dirname(UPLOAD_BASE_DIR)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 1. SETTINGS & CONFIGURACIÓN CENTRAL
@router.get("/api/admin/settings")
def get_admin_settings(admin: AdminUser = Depends(require_admin_role), db: Session = Depends(get_db)):
    """Retorna todas las configuraciones almacenadas en la base de datos."""
    return get_all_settings(db)

@router.put("/api/admin/settings")
def update_admin_settings(
    data: BulkSettingsUpdate,
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Actualiza en lote múltiples parámetros de configuración del sistema."""
    old_sets = get_all_settings(db)
    bulk_set_settings(db, data.settings)

    db.add(AuditLog(
        user_name=admin.username,
        module="Configuración",
        action="Actualizar Ajustes",
        old_value="Valores previos actualizados",
        new_value=json.dumps(data.settings, default=str)[:300]
    ))
    db.commit()

    return {"message": "Configuración actualizada correctamente.", "settings": get_all_settings(db)}

# 2. SUBIDA DE ARCHIVOS / RECURSOS VISUALES
@router.post("/api/admin/upload")
async def upload_asset(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(require_admin_role)
):
    """Subida genérica de archivos visuales o multimedia."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo no válido.")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg", ".mp3", ".mp4"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Formato de archivo no permitido. Permitidos: {allowed_exts}")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo supera el tamaño máximo permitido (5 MB).")

    filename = f"asset_{get_argentina_now().strftime('%Y%m%d_%H%M%S')}_{file.filename.replace(' ', '_')}"
    filepath = os.path.join(UPLOADS_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    file_url = f"/static/uploads/{filename}"
    return {"status": "success", "file_url": file_url, "filename": filename}

@router.post("/api/admin/logo/upload")
async def upload_logo(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Subida de logotipo de la barbería."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se seleccionó ningún archivo.")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".png", ".jpg", ".jpeg", ".webp", ".svg"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Formato no permitido ({ext}). Formatos aceptados: PNG (con transparencia), JPG, WebP, SVG.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El logo supera el tamaño máximo permitido (5 MB).")

    old_logo = get_setting(db, "logo_url", "")
    if old_logo:
        delete_orphan_file(old_logo)

    filename = f"logo_{get_argentina_now().strftime('%Y%m%d_%H%M%S')}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    logo_url = f"/static/uploads/{filename}"
    bulk_set_settings(db, {"logo_url": logo_url})

    db.add(AuditLog(
        user_name=admin.username,
        module="Identidad",
        action="Subir Logo",
        new_value=logo_url
    ))
    db.commit()

    return {"status": "success", "logo_url": logo_url, "message": "Logo actualizado y guardado correctamente."}

@router.delete("/api/admin/logo/delete")
def delete_logo(
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Elimina el logo de la barbería y borra el archivo huérfano."""
    old_logo = get_setting(db, "logo_url", "")
    if old_logo:
        delete_orphan_file(old_logo)

    bulk_set_settings(db, {"logo_url": ""})
    db.add(AuditLog(
        user_name=admin.username,
        module="Identidad",
        action="Eliminar Logo",
        old_value="Logo eliminado"
    ))
    db.commit()
    return {"status": "success", "logo_url": "", "message": "Logo eliminado correctamente."}

# 3. MOTOR MULTIMEDIA UNIVERSAL
@router.post("/api/media/upload")
async def upload_media_asset(
    file: UploadFile = File(...),
    context: str = Form(...),
    previous_url: Optional[str] = Form(None),
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Motor universal de carga y procesamiento de imágenes con Pillow y compresión WebP."""
    clean_context = context.strip().lower()
    user_role = (current_user.role or "").lower()

    if clean_context in ["product", "branding"]:
        if user_role not in ["admin", "encargado"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Se requiere rol ENCARGADO o ADMIN para subir activos de producto o branding."
            )
    elif clean_context == "avatar":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Debe iniciar sesión para actualizar la imagen de perfil."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contexto '{context}' no válido. Use 'avatar', 'product' o 'branding'."
        )

    try:
        contents = await file.read()
        result = process_and_save_image(
            file_bytes=contents,
            original_filename=file.filename or "uploaded_image.jpg",
            context=clean_context,
            previous_url=previous_url
        )

        db.add(AuditLog(
            user_name=current_user.username,
            actor=current_user.username,
            module="Multimedia",
            action=f"UPLOAD_{clean_context.upper()}",
            new_value=result["url"],
            description=f"Subida de imagen ({clean_context}): {result['filename']} ({result['width']}x{result['height']} px)"
        ))
        db.commit()

        return result
    except ImageProcessingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception(f"Error inesperado en upload_media_asset: {e}")
        raise HTTPException(status_code=500, detail="Error interno al procesar el archivo multimedia.")

@router.delete("/api/media/delete")
def delete_media_asset(
    file_url: str = Query(...),
    current_user: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Elimina de forma segura un archivo multimedia huérfano dentro de uploads."""
    deleted = delete_orphan_file(file_url)
    if deleted:
        db.add(AuditLog(
            user_name=current_user.username,
            actor=current_user.username,
            module="Multimedia",
            action="DELETE_MEDIA",
            description=f"Eliminación de recurso multimedia: {file_url}"
        ))
        db.commit()
        return {"status": "success", "message": "Archivo eliminado correctamente."}
    return {"status": "not_found", "message": "El archivo no existe o no se encuentra dentro del directorio permitido."}

# 4. EXPORTAR / IMPORTAR CONFIGURACIÓN CENTRALIZADA
@router.get("/api/admin/config/export")
def export_application_config(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_role)
):
    """Exporta las configuraciones de la barbería excluyendo secretos, claves de API y contraseñas."""
    settings = get_all_settings(db)
    safe_settings = {}
    sensitive_keys = {"token", "secret", "password", "key", "access_token"}
    for k, v in settings.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            continue
        safe_settings[k] = v

    return {
        "export_date": get_argentina_now().isoformat(),
        "exported_by": admin.username,
        "settings_count": len(safe_settings),
        "settings": safe_settings
    }

@router.post("/api/admin/config/import")
def import_application_config(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin_role)
):
    """Importa configuraciones visuales y operativas validadas."""
    settings_to_import = data.get("settings", data)
    sensitive_keys = {"token", "secret", "password", "key", "access_token"}
    imported_count = 0

    for k, v in settings_to_import.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            continue
        set_setting(db, k, str(v))
        imported_count += 1

    db.commit()
    db.add(AuditLog(
        user_name=admin.username,
        module="Configuración",
        action="Importar Configuración",
        description=f"Importadas {imported_count} configuraciones"
    ))
    db.commit()
    return {"status": "success", "message": f"{imported_count} configuraciones importadas exitosamente."}

# 5. AUDITORÍA Y NOTIFICACIONES
@router.get("/api/admin/audit-logs", response_model=List[AuditLogRead])
@router.get("/api/audit-logs", response_model=List[AuditLogRead], deprecated=True)
def get_audit_logs(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Consulta de logs de auditoría de seguridad y operaciones del sistema."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if actor:
        query = query.filter(or_(AuditLog.actor.ilike(f"%{actor}%"), AuditLog.user_name.ilike(f"%{actor}%")))
    if search:
        s_term = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.description.ilike(s_term),
                AuditLog.action.ilike(s_term),
                AuditLog.actor.ilike(s_term),
                AuditLog.user_name.ilike(s_term),
                AuditLog.module.ilike(s_term)
            )
        )

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    res = []
    for l in logs:
        item = AuditLogRead.model_validate(l)
        item.actor = l.actor or l.user_name or "Encargado / Recepción"
        item.description = l.description or f"{l.action} en módulo {l.module}"
        res.append(item)
    return res

@router.get("/api/admin/notifications/logs", response_model=List[NotificationLogRead])
def get_admin_notification_logs(
    limit: int = 200,
    status: Optional[str] = None,
    message_type: Optional[str] = None,
    search: Optional[str] = None,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Consulta el registro histórico de notificaciones WhatsApp enviadas con filtros avanzados."""
    query = db.query(NotificationLog)
    if status and status.upper() != "TODOS":
        query = query.filter(NotificationLog.status == status.upper())
    if message_type and message_type.upper() != "TODOS":
        query = query.filter(NotificationLog.message_type == message_type.upper())
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                NotificationLog.recipient.ilike(s),
                NotificationLog.message_body.ilike(s),
                NotificationLog.message_type.ilike(s),
                NotificationLog.status.ilike(s)
            )
        )
    return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()

@router.delete("/api/admin/notifications/logs/{log_id}")
def delete_single_notification_log(
    log_id: int,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Elimina un registro individual de auditoría de WhatsApp."""
    log_item = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
    if not log_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    db.delete(log_item)
    db.commit()
    return {"status": "success", "message": f"Registro #{log_id} eliminado."}

@router.post("/api/admin/notifications/logs/bulk-delete")
def bulk_delete_notification_logs(
    payload: dict,
    admin: AdminUser = Depends(require_encargado_or_admin),
    db: Session = Depends(get_db)
):
    """Elimina en lote una selección de registros de auditoría de WhatsApp."""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No se enviaron IDs para eliminar.")
    count = db.query(NotificationLog).filter(NotificationLog.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"Se eliminaron {count} registros de notificaciones."}

