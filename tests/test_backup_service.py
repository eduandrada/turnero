"""
tests/test_backup_service.py - Comprehensive tests for BackupService and adapters.
Covers:
- Backup creation
- Listing
- Path traversal rejection (security)
- Pre-restore automatic backup
- SQLite and PostgreSQL adapter selection
"""
import os
import pytest
from app.services.backup_service import BackupService, SQLiteBackupAdapter, PostgreSQLBackupAdapter
from app.core.exceptions import SecurityError
from fastapi import HTTPException


def test_backup_service_creation_and_listing(tmp_path, db_session):
    backups_dir = tmp_path / "backups"
    service = BackupService(backup_directory=str(backups_dir))
    
    # 1. Create backup
    filename = service.create_backup(db=db_session, user_name="TestAdmin")
    assert filename is not None
    assert filename.startswith("backup_barberia_")
    
    # 2. List backups
    listing = service.list_backups()
    assert len(listing) == 1
    assert listing[0]["filename"] == filename
    assert listing[0]["size_bytes"] > 0


def test_backup_service_path_traversal_rejection(tmp_path, db_session):
    backups_dir = tmp_path / "backups"
    service = BackupService(backup_directory=str(backups_dir))
    service.create_backup(db=db_session)
    
    # Malicious filenames attempting traversal
    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "/etc/shadow",
        "C:\\Windows\\System32\\calc.exe",
        "sub/../../secret.db"
    ]
    
    for payload in traversal_payloads:
        with pytest.raises((SecurityError, HTTPException)):
            service.get_backup_path(payload)
            
        with pytest.raises((SecurityError, HTTPException)):
            service.restore_backup(db=db_session, filename=payload)


def test_backup_service_pre_restore_backup(tmp_path, db_session):
    backups_dir = tmp_path / "backups"
    service = BackupService(backup_directory=str(backups_dir))
    
    # Create initial backup
    bk1 = service.create_backup(db=db_session, user_name="AdminInitial")
    assert len(service.list_backups()) == 1
    
    # Restore bk1 with automated pre_backup
    restored = service.restore_backup(db=db_session, filename=bk1, user_name="AdminRestorer")
    assert restored is True
    
    # List backups must contain bk1 and the auto-saved pre-restore backup
    listing = service.list_backups()
    assert len(listing) == 2


def test_adapter_selection():
    service = BackupService()
    assert isinstance(service.adapter, (SQLiteBackupAdapter, PostgreSQLBackupAdapter))
