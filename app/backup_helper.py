"""
app/backup_helper.py - Backward compatibility facade for database backups.
Delegates all operations to the new robust app.services.backup_service.BackupService.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import BACKUP_DIR
from app.services.backup_service import (
    backup_service,
    BackupService,
    SQLiteBackupAdapter,
    PostgreSQLBackupAdapter,
)

def ensure_backup_dir():
    backup_service._ensure_dir()

def create_database_backup(db: Session, user_name: str = "Administrador") -> str:
    return backup_service.create_backup(db=db, user_name=user_name)

def list_backups() -> List[Dict[str, Any]]:
    return backup_service.list_backups()

def restore_database_backup(db: Session, filename: str, user_name: str = "Administrador") -> bool:
    return backup_service.restore_backup(db=db, filename=filename, user_name=user_name)

def verify_backup_integrity(filename: str) -> Dict[str, Any]:
    return backup_service.verify_integrity(filename=filename)

def cleanup_old_backups(retention_days: int = 30, min_to_keep: int = 5) -> Dict[str, int]:
    return backup_service.cleanup_old_backups(retention_days=retention_days, min_to_keep=min_to_keep)

__all__ = [
    "BACKUP_DIR",
    "backup_service",
    "BackupService",
    "SQLiteBackupAdapter",
    "PostgreSQLBackupAdapter",
    "ensure_backup_dir",
    "create_database_backup",
    "list_backups",
    "restore_database_backup",
    "verify_backup_integrity",
    "cleanup_old_backups",
]
