"""
app/services/backup_service.py - Comprehensive, multi-engine database backup & restore service.
Supports both SQLite and PostgreSQL with automated pre-restore safeguards, integrity verification,
path traversal defense via safe_path(), and audit logging.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text, Engine
from sqlalchemy.orm import Session

from app.core.config import DATABASE_URL, BACKUP_DIR
from app.core.database import engine, get_argentina_now
from app.core.path_security import safe_path
from app.core.logging import backup_logger, audit_logger
from app.models import AuditLog

logger = backup_logger


class BaseBackupAdapter:
    """Interface for database-specific backup and restore operations."""
    def export_data(self, engine: Engine) -> Dict[str, Any]:
        raise NotImplementedError

    def import_data(self, engine: Engine, data: Dict[str, Any]) -> None:
        raise NotImplementedError


class SQLiteBackupAdapter(BaseBackupAdapter):
    """Backup adapter for SQLite engines."""
    
    def export_data(self, engine: Engine) -> Dict[str, Any]:
        tables_data = {}
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        with engine.connect() as conn:
            for table in table_names:
                if table.startswith("sqlite_"):
                    continue
                columns = [c["name"] for c in inspector.get_columns(table)]
                result = conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = [list(r) for r in result.fetchall()]
                tables_data[table] = {
                    "columns": columns,
                    "rows": rows
                }
        return tables_data

    def import_data(self, engine: Engine, data: Dict[str, Any]) -> None:
        tables_dict = data.get("tables", data)
        with engine.begin() as conn:
            # Desactivar temporalmente foreign keys en SQLite
            conn.execute(text("PRAGMA foreign_keys = OFF;"))
            for table_name, table_info in tables_dict.items():
                if table_name.startswith("sqlite_") or not isinstance(table_info, dict):
                    continue
                columns = table_info.get("columns", [])
                rows = table_info.get("rows", [])
                if not columns:
                    continue
                
                # Limpiar tabla
                conn.execute(text(f'DELETE FROM "{table_name}";'))
                
                if rows:
                    col_quoted = ", ".join([f'"{c}"' for c in columns])
                    param_placeholders = ", ".join([f":col_{i}" for i in range(len(columns))])
                    insert_sql = text(f'INSERT INTO "{table_name}" ({col_quoted}) VALUES ({param_placeholders})')
                    
                    param_rows = [
                        {f"col_{i}": row[i] for i in range(len(columns))}
                        for row in rows
                    ]
                    conn.execute(insert_sql, param_rows)
            conn.execute(text("PRAGMA foreign_keys = ON;"))


class PostgreSQLBackupAdapter(BaseBackupAdapter):
    """Backup adapter for PostgreSQL engines."""
    
    def export_data(self, engine: Engine) -> Dict[str, Any]:
        tables_data = {}
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        with engine.connect() as conn:
            for table in table_names:
                if table.startswith("pg_"):
                    continue
                columns = [c["name"] for c in inspector.get_columns(table)]
                result = conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = [list(r) for r in result.fetchall()]
                tables_data[table] = {
                    "columns": columns,
                    "rows": rows
                }
        return tables_data

    def import_data(self, engine: Engine, data: Dict[str, Any]) -> None:
        tables_dict = data.get("tables", data)
        with engine.begin() as conn:
            # Desactivar temporalmente constraints o usar TRUNCATE CASCADE
            for table_name, table_info in tables_dict.items():
                if table_name.startswith("pg_") or not isinstance(table_info, dict):
                    continue
                columns = table_info.get("columns", [])
                rows = table_info.get("rows", [])
                if not columns:
                    continue

                conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
                
                if rows:
                    col_quoted = ", ".join([f'"{c}"' for c in columns])
                    param_placeholders = ", ".join([f":col_{i}" for i in range(len(columns))])
                    insert_sql = text(f'INSERT INTO "{table_name}" ({col_quoted}) VALUES ({param_placeholders})')
                    
                    param_rows = [
                        {f"col_{i}": row[i] for i in range(len(columns))}
                        for row in rows
                    ]
                    conn.execute(insert_sql, param_rows)


class BackupService:
    """High-level service managing backup lifecycle, storage, validation and restoration."""

    def __init__(self, backup_directory: str = BACKUP_DIR):
        self.backup_dir = backup_directory
        self._ensure_dir()
        self.adapter = self._resolve_adapter()

    def _ensure_dir(self) -> None:
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)

    def _resolve_adapter(self) -> BaseBackupAdapter:
        if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
            logger.info("BackupService: Inicializado adaptador para PostgreSQL.")
            return PostgreSQLBackupAdapter()
        logger.info("BackupService: Inicializado adaptador para SQLite.")
        return SQLiteBackupAdapter()

    def get_backup_path(self, filename: str) -> str:
        """Obtiene y valida la ruta absoluta del archivo evitando path traversal."""
        return safe_path(self.backup_dir, filename)

    def create_backup(self, db: Session, user_name: str = "Administrador") -> str:
        """Genera un archivo JSON de respaldo completo de la base de datos."""
        self._ensure_dir()
        timestamp = get_argentina_now().strftime("%Y%m%d_%H%M%S_%f")[:22]
        filename = f"backup_barberia_{timestamp}.json"
        filepath = safe_path(self.backup_dir, filename)

        engine_type = "postgresql" if "postgres" in DATABASE_URL else "sqlite"
        raw_tables = self.adapter.export_data(engine)

        backup_payload = {
            "meta": {
                "created_at": get_argentina_now().isoformat(),
                "engine": engine_type,
                "version": "2.0",
                "created_by": user_name
            },
            "tables": raw_tables
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, indent=2, default=str)

        # Registro de auditoría
        try:
            db.add(AuditLog(
                user_name=user_name,
                module="Copias de Seguridad",
                action="Crear Backup",
                record_id=filename,
                new_value=f"Backup guardado exitosamente en {filename} ({len(raw_tables)} tablas)"
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Error registrando auditoría de backup: {e}")

        logger.info(f"Backup creado exitosamente: {filename}")
        return filename

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todas las copias de seguridad disponibles ordenadas de más reciente a más antigua."""
        self._ensure_dir()
        result = []
        for f in os.listdir(self.backup_dir):
            if f.endswith(".json") or f.endswith(".db"):
                try:
                    fpath = safe_path(self.backup_dir, f)
                    stat = os.stat(fpath)
                    result.append({
                        "filename": f,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception:
                    continue
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    def verify_integrity(self, filename: str) -> Dict[str, Any]:
        """Comprueba que el archivo exista, sea JSON válido y posea estructura coherente."""
        try:
            filepath = safe_path(self.backup_dir, filename)
        except Exception as e:
            return {"valid": False, "error": f"Ruta inválida: {str(e)}"}

        if not os.path.exists(filepath):
            return {"valid": False, "error": "Archivo no encontrado"}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or not data:
                return {"valid": False, "error": "El archivo de backup está vacío o no es un diccionario JSON"}

            # Soportar tanto formato nuevo {"meta": ..., "tables": ...} como formato legado {table: {columns, rows}}
            tables_dict = data.get("tables", data)
            total_rows = 0
            tables_summary = {}

            for table_name, table_data in tables_dict.items():
                if table_name == "meta" or not isinstance(table_data, dict):
                    continue
                cols = table_data.get("columns", [])
                rows = table_data.get("rows", [])
                tables_summary[table_name] = {
                    "columns_count": len(cols),
                    "rows_count": len(rows)
                }
                total_rows += len(rows)

            return {
                "valid": True,
                "filename": filename,
                "tables_count": len(tables_summary),
                "total_rows": total_rows,
                "tables": tables_summary
            }
        except Exception as e:
            return {"valid": False, "error": f"Error de formato o JSON corrupto: {str(e)}"}

    def restore_backup(self, db: Session, filename: str, user_name: str = "Administrador") -> bool:
        """
        Restaura de forma segura un respaldo previo:
        1. Valida ruta mediante safe_path().
        2. Verifica integridad antes de ejecutar.
        3. Realiza un respaldo preventivo de seguridad automático.
        4. Ejecuta la restauración en transacción.
        5. Deja registro de auditoría.
        """
        filepath = safe_path(self.backup_dir, filename)
        if not os.path.exists(filepath):
            logger.error(f"Restauración fallida: Archivo {filename} no existe.")
            return False

        # 1. Verificación previa de integridad
        integrity = self.verify_integrity(filename)
        if not integrity.get("valid"):
            logger.error(f"Restauración abortada: Integridad corrupta en {filename}: {integrity.get('error')}")
            return False

        # 2. Respaldo automático antes de restaurar
        auto_backup_file = self.create_backup(db, user_name=f"AutoBeforeRestore_{user_name}")

        # 3. Cargar y procesar datos
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            self.adapter.import_data(engine, data)
        except Exception as e:
            logger.error(f"Error crítico durante importación de datos en restauración: {e}")
            raise e

        # 4. Auditoría
        try:
            db.add(AuditLog(
                user_name=user_name,
                module="Copias de Seguridad",
                action="Restaurar Backup",
                record_id=filename,
                old_value=f"Backup previo auto-guardado como {auto_backup_file}",
                new_value=f"Base de datos restaurada exitosamente desde {filename}"
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Error registrando auditoría de restauración: {e}")

        logger.info(f"Restauración de base de datos completada exitosamente desde {filename}")
        return True

    def cleanup_old_backups(self, retention_days: int = 30, min_to_keep: int = 5) -> Dict[str, int]:
        """Elimina copias de seguridad antiguas conservando un mínimo requerido."""
        self._ensure_dir()
        all_backups = self.list_backups()
        if len(all_backups) <= min_to_keep:
            return {"deleted": 0, "kept": len(all_backups)}

        now = datetime.now()
        deleted_count = 0
        candidates = all_backups[min_to_keep:]
        for b in candidates:
            try:
                created_dt = datetime.fromisoformat(b["created_at"])
                age_days = (now - created_dt).days
                if age_days > retention_days:
                    fpath = safe_path(self.backup_dir, b["filename"])
                    if os.path.exists(fpath):
                        os.remove(fpath)
                        deleted_count += 1
            except Exception:
                continue

        return {"deleted": deleted_count, "kept": len(all_backups) - deleted_count}


# Instancia singleton predeterminada
backup_service = BackupService()
