"""
app/api/admin/backups.py - Endpoints de Gestión Segura de Copias de Seguridad
HiddenSYNC AI 2026
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AdminUser
from app.core.dependencies import require_admin_role
from app.core.path_security import safe_path
from app.backup_helper import (
    create_database_backup,
    list_backups,
    restore_database_backup,
    BACKUP_DIR,
    verify_backup_integrity,
    cleanup_old_backups
)

router = APIRouter(tags=["Admin Backups"])

@router.get("/api/admin/backups")
def get_admin_backups(admin: AdminUser = Depends(require_admin_role)):
    """Lista las copias de seguridad disponibles con metadatos de integridad."""
    return list_backups()

@router.post("/api/admin/backups/create")
def create_admin_backup(
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Genera una nueva copia de seguridad atómica compatible con SQLite o PostgreSQL."""
    fname = create_database_backup(db, user_name=admin.username)
    return {"message": "Copia de seguridad creada correctamente.", "filename": fname}

@router.post("/api/admin/backups/restore")
def restore_admin_backup(
    filename: str = Query(...),
    admin: AdminUser = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Restaura la base de datos previa verificación criptográfica y respaldo preventivo de seguridad."""
    ok = restore_database_backup(db, filename, user_name=admin.username)
    if not ok:
        raise HTTPException(status_code=400, detail="No se pudo restaurar el archivo de backup especificado.")
    return {"message": f"Base de datos restaurada exitosamente desde '{filename}'."}

@router.get("/api/admin/backups/download/{filename}")
def download_admin_backup(
    filename: str,
    admin: AdminUser = Depends(require_admin_role)
):
    """Descarga de un archivo de backup protegido contra path traversal con safe_path."""
    fpath = safe_path(BACKUP_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(fpath, media_type="application/json", filename=filename)

@router.get("/api/admin/backups/verify/{filename}")
def verify_admin_backup(
    filename: str,
    admin: AdminUser = Depends(require_admin_role)
):
    """Verifica la integridad física y lógica de un archivo de backup JSON."""
    result = verify_backup_integrity(filename)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Backup corrupto o inválido."))
    return result

@router.post("/api/admin/backups/cleanup")
def cleanup_admin_backups(
    retention_days: int = Query(30, ge=1, le=365),
    min_to_keep: int = Query(5, ge=1, le=50),
    admin: AdminUser = Depends(require_admin_role)
):
    """Aplica la política de retención de backups eliminando copias antiguas."""
    return cleanup_old_backups(retention_days=retention_days, min_to_keep=min_to_keep)
