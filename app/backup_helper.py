import os
import json
import sqlite3
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_argentina_now, DATABASE_URL, engine
from app.models import AuditLog

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")

def ensure_backup_dir():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)

def create_database_backup(db: Session, user_name: str = "Administrador") -> str:
    ensure_backup_dir()
    timestamp = get_argentina_now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_barberia_{timestamp}.json"
    filepath = os.path.join(BACKUP_DIR, filename)

    # Dump all tables to JSON backup file
    data = {}
    with engine.connect() as conn:
        inspector = sqlite3.connect(DATABASE_URL.replace("sqlite:///", "")) if "sqlite" in DATABASE_URL else None
        if inspector:
            cur = inspector.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                if t.startswith("sqlite_"): continue
                cols = [c[1] for c in cur.execute(f"PRAGMA table_info('{t}')").fetchall()]
                rows = cur.execute(f"SELECT * FROM '{t}'").fetchall()
                data[t] = {
                    "columns": cols,
                    "rows": rows
                }
            inspector.close()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    # Log audit
    db.add(AuditLog(
        user_name=user_name,
        module="Copias de Seguridad",
        action="Crear Backup",
        record_id=filename,
        new_value=f"Backup guardado en {filename}"
    ))
    db.commit()

    return filename

def list_backups() -> list:
    ensure_backup_dir()
    result = []
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".json") or f.endswith(".db"):
            fpath = os.path.join(BACKUP_DIR, f)
            stat = os.stat(fpath)
            result.append({
                "filename": f,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result

def restore_database_backup(db: Session, filename: str, user_name: str = "Administrador") -> bool:
    ensure_backup_dir()
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False

    # Auto backup before restore
    auto_filename = create_database_backup(db, user_name=f"AutoBeforeRestore_{user_name}")

    if filepath.endswith(".json"):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        db_file = DATABASE_URL.replace("sqlite:///", "")
        if "sqlite" in DATABASE_URL and os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            for tname, tdata in data.items():
                if tname.startswith("sqlite_"): continue
                cols = tdata.get("columns", [])
                rows = tdata.get("rows", [])
                if not cols: continue
                
                # Delete existing rows
                cur.execute(f"DELETE FROM '{tname}'")
                placeholders = ",".join(["?"] * len(cols))
                col_names = ",".join([f"'{c}'" for c in cols])
                sql = f"INSERT INTO '{tname}' ({col_names}) VALUES ({placeholders})"
                for row in rows:
                    cur.execute(sql, row)
            conn.commit()
            conn.close()

    db.add(AuditLog(
        user_name=user_name,
        module="Copias de Seguridad",
        action="Restaurar Backup",
        record_id=filename,
        old_value=f"Backup previo auto-guardado como {auto_filename}",
        new_value=f"Restaurado desde {filename}"
    ))
    db.commit()
    return True
