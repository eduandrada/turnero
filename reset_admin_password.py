"""
reset_admin_password.py - Herramienta CLI para restablecer o verificar la contraseña del Administrador
HiddenSYNC AI 2026

Uso:
    python reset_admin_password.py [NUEVA_CONTRASEÑA]

Ejemplo:
    python reset_admin_password.py
    (Restablece la contraseña a 'admin123' por defecto)

    python reset_admin_password.py MiClaveSegura2026!
"""
import sys
import os

# Asegurar path del proyecto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import AdminUser
from app.core.security import hash_password

def main():
    new_password = sys.argv[1].strip() if len(sys.argv) > 1 else "admin123"

    db = SessionLocal()
    try:
        admin_user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin_user:
            admin_user = AdminUser(
                username="admin",
                password_hash=hash_password(new_password),
                role="admin",
                is_active=True,
                can_edit_stock=True,
                can_view_finances=True,
                can_cancel_appointments=True,
                can_manage_shop=True
            )
            db.add(admin_user)
            print("[+] Usuario 'admin' no existia. Ha sido creado exitosamente.")
        else:
            admin_user.password_hash = hash_password(new_password)
            admin_user.is_active = True
            admin_user.role = "admin"
            admin_user.can_edit_stock = True
            admin_user.can_view_finances = True
            admin_user.can_cancel_appointments = True
            admin_user.can_manage_shop = True
            print("[+] Contraseña del usuario 'admin' actualizada exitosamente.")

        db.commit()

        print("\n" + "=" * 50)
        print(" CREDENCIALES DEL PANEL ADMINISTRATIVO (HiddenSYNC)")
        print("=" * 50)
        print(f" URL:        http://127.0.0.1:8000/admin.html")
        print(f" Usuario:    admin")
        print(f" Contraseña: {new_password}")
        print("=" * 50 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[!] Error al actualizar credenciales: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
