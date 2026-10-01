"""
tests/test_universal_media_and_gatekeeper.py
Pruebas exhaustivas para:
1. Validación de APP_SECRET_KEY en producción y configuración limpia.
2. Integración y ciclo de vida de APScheduler.
3. Motor universal de procesamiento de imágenes con Pillow (WebP, dimensiones por contexto, limpieza de huérfanos).
4. Endpoint RBAC POST /api/media/upload y DELETE /api/media/delete.
5. Control de acceso y Staff Gatekeeper en shop.html.
"""

import io
import os
import pytest
from PIL import Image

from app.config import verify_production_secrets, get_secret_key
from app.scheduler import start_scheduler, shutdown_scheduler, is_scheduler_running
from app.image_service import (
    process_and_save_image,
    delete_orphan_file,
    ImageProcessingError,
    UPLOAD_BASE_DIR,
)


# ==============================================================================
# 1. PRUEBAS DE CONFIGURACIÓN Y APP_SECRET_KEY
# ==============================================================================
def test_production_secret_key_aborts_if_missing_or_default(monkeypatch):
    """En producción (ENV=production), la app debe abortar el arranque si no hay clave o es insegura."""
    monkeypatch.setenv("ENV", "production")

    # Clave vacía
    monkeypatch.setenv("APP_SECRET_KEY", "")
    monkeypatch.setenv("SECRET_KEY", "")
    with pytest.raises(RuntimeError) as exc_info:
        verify_production_secrets()
    assert "CRÍTICO DE SEGURIDAD" in str(exc_info.value)

    # Clave por defecto / plantilla
    monkeypatch.setenv("APP_SECRET_KEY", "hiddensync_secret_key_barberia_2026_x99")
    with pytest.raises(RuntimeError) as exc_info:
        verify_production_secrets()
    assert "CRÍTICO DE SEGURIDAD" in str(exc_info.value)

    # Clave demasiado corta (< 16 caracteres)
    monkeypatch.setenv("APP_SECRET_KEY", "clave_corta_123")
    with pytest.raises(RuntimeError) as exc_info:
        verify_production_secrets()
    assert "al menos 16 caracteres" in str(exc_info.value)

    # Clave segura en producción: debe pasar sin errores
    monkeypatch.setenv("APP_SECRET_KEY", "clave_ultra_secreta_para_produccion_2026_segura_32char")
    verify_production_secrets()
    assert get_secret_key() == "clave_ultra_secreta_para_produccion_2026_segura_32char"


def test_development_environment_allows_fallback_secret(monkeypatch):
    """En desarrollo (ENV=development), se permite fallback sin lanzar excepción."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("APP_SECRET_KEY", "")
    monkeypatch.setenv("SECRET_KEY", "")

    # No debe lanzar excepción
    verify_production_secrets()
    assert get_secret_key() == "hiddensync_secret_key_barberia_2026_x99"


# ==============================================================================
# 2. PRUEBAS DE APSCHEDULER LIFECYCLE
# ==============================================================================
def test_apscheduler_lifecycle():
    """Verifica que el planificador pueda iniciar y detenerse formalmente."""
    start_scheduler()
    assert is_scheduler_running() is True

    shutdown_scheduler()
    assert is_scheduler_running() is False


# ==============================================================================
# 3. PRUEBAS DEL MOTOR UNIVERSAL DE IMÁGENES (Pillow + WebP)
# ==============================================================================
def _create_test_image_bytes(width: int = 1000, height: int = 600, fmt: str = "PNG", color: str = "blue") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_image_service_rejects_invalid_file_payloads():
    """Valida rechazo de archivos vacíos, extensiones no permitidas y bytes corruptos."""
    # Archivo vacío
    with pytest.raises(ImageProcessingError) as exc:
        process_and_save_image(b"", "foto.png", "product")
    assert "está vacío" in str(exc.value)

    # Extensión no permitida
    sample_bytes = _create_test_image_bytes(100, 100)
    with pytest.raises(ImageProcessingError) as exc:
        process_and_save_image(sample_bytes, "script.exe", "product")
    assert "Extensión no permitida" in str(exc.value)

    # Bytes corruptos / fingir ser imagen
    fake_png = b"\x89PNG\r\n\x1a\nCorruptBytesDataNotRealImage"
    with pytest.raises(ImageProcessingError) as exc:
        process_and_save_image(fake_png, "corrupt.png", "product")
    assert "bytes corruptos" in str(exc.value)


def test_image_service_context_avatar_cropping():
    """Verifica que el contexto 'avatar' recorte centrado a 300x300 en formato WebP."""
    raw_bytes = _create_test_image_bytes(800, 400, fmt="JPEG", color="red")
    result = process_and_save_image(raw_bytes, "foto_perfil.jpg", "avatar")

    assert result["status"] == "success"
    assert result["context"] == "avatar"
    assert result["filename"].endswith(".webp")
    assert result["width"] == 300
    assert result["height"] == 300
    assert result["size_bytes"] > 0
    assert "/static/uploads/avatars/" in result["url"]

    # Limpieza
    deleted = delete_orphan_file(result["url"])
    assert deleted is True


def test_image_service_context_product_aspect_ratio():
    """Verifica que el contexto 'product' escale preservando relación de aspecto dentro de 800x800."""
    raw_bytes = _create_test_image_bytes(1200, 600, fmt="PNG", color="green")
    result = process_and_save_image(raw_bytes, "pomada.png", "product")

    assert result["status"] == "success"
    assert result["context"] == "product"
    assert result["filename"].endswith(".webp")
    # 1200x600 scaled into 800x800 -> 800x400
    assert result["width"] == 800
    assert result["height"] == 400
    assert "/static/uploads/products/" in result["url"]

    # Limpieza
    assert delete_orphan_file(result["url"]) is True


def test_image_service_context_branding_scaling():
    """Verifica que el contexto 'branding' escale a máx 600 px de ancho manteniendo proporciones."""
    raw_bytes = _create_test_image_bytes(1000, 500, fmt="JPEG", color="purple")
    result = process_and_save_image(raw_bytes, "logo_local.jpeg", "branding")

    assert result["status"] == "success"
    assert result["context"] == "branding"
    assert result["filename"].endswith(".webp")
    assert result["width"] == 600
    assert result["height"] == 300
    assert "/static/uploads/branding/" in result["url"]

    # Limpieza
    assert delete_orphan_file(result["url"]) is True


def test_image_service_orphan_cleanup_and_security():
    """Verifica que la limpieza de archivos huérfanos funcione y bloquee intentos de Path Traversal."""
    raw_bytes = _create_test_image_bytes(200, 200, fmt="PNG")
    result1 = process_and_save_image(raw_bytes, "img1.png", "product")
    url1 = result1["url"]

    # Subir imagen 2 indicando que reemplaza imagen 1
    result2 = process_and_save_image(raw_bytes, "img2.png", "product", previous_url=url1)

    # La imagen 1 debe haber sido eliminada automáticamente del disco
    assert delete_orphan_file(url1) is False  # Ya fue borrada

    # La imagen 2 debe existir
    assert delete_orphan_file(result2["url"]) is True

    # Intento de Path Traversal hacia directorios superiores
    assert delete_orphan_file("../../etc/passwd") is False
    assert delete_orphan_file("/etc/shadow") is False


# ==============================================================================
# 4. PRUEBAS DEL ENDPOINT POST /api/media/upload Y DELETE /api/media/delete
# ==============================================================================
def test_media_upload_endpoint_rbac(client, admin_token, encargado_token, barbero_token):
    """Verifica control de acceso según rol y contexto en /api/media/upload."""
    sample_img = _create_test_image_bytes(400, 400, fmt="JPEG")

    # 1. Petición no autenticada rechazada con 401
    res_no_auth = client.post(
        "/api/media/upload",
        data={"context": "product"},
        files={"file": ("test.jpg", sample_img, "image/jpeg")}
    )
    assert res_no_auth.status_code == 401

    # 2. Barbero intentando subir producto -> 403 Prohibido
    res_barbero_prod = client.post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {barbero_token}"},
        data={"context": "product"},
        files={"file": ("test.jpg", sample_img, "image/jpeg")}
    )
    assert res_barbero_prod.status_code == 403

    # 3. Barbero intentando subir branding -> 403 Prohibido
    res_barbero_brand = client.post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {barbero_token}"},
        data={"context": "branding"},
        files={"file": ("test.jpg", sample_img, "image/jpeg")}
    )
    assert res_barbero_brand.status_code == 403

    # 4. Barbero subiendo su avatar -> 200 OK
    res_barbero_avatar = client.post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {barbero_token}"},
        data={"context": "avatar"},
        files={"file": ("avatar.jpg", sample_img, "image/jpeg")}
    )
    assert res_barbero_avatar.status_code == 200
    avatar_data = res_barbero_avatar.json()
    assert avatar_data["status"] == "success"
    assert avatar_data["context"] == "avatar"
    assert avatar_data["width"] == 300
    assert avatar_data["height"] == 300
    delete_orphan_file(avatar_data["url"])

    # 5. Encargado subiendo producto -> 200 OK
    res_encargado_prod = client.post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {encargado_token}"},
        data={"context": "product"},
        files={"file": ("producto.png", sample_img, "image/png")}
    )
    assert res_encargado_prod.status_code == 200
    prod_data = res_encargado_prod.json()
    assert prod_data["status"] == "success"
    assert prod_data["context"] == "product"
    assert prod_data["filename"].endswith(".webp")

    # 6. Admin subiendo branding y reemplazando el anterior
    res_admin_brand = client.post(
        "/api/media/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"context": "branding", "previous_url": prod_data["url"]},
        files={"file": ("logo.png", sample_img, "image/png")}
    )
    assert res_admin_brand.status_code == 200
    brand_data = res_admin_brand.json()
    assert brand_data["status"] == "success"
    assert brand_data["context"] == "branding"

    # Verificar que el producto anterior fue limpiado por previous_url
    assert delete_orphan_file(prod_data["url"]) is False

    # Eliminar imagen de branding creada
    res_del = client.delete(
        f"/api/media/delete?file_url={brand_data['url']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_del.status_code == 200


# ==============================================================================
# 5. PRUEBAS DE INTERFAZ Y STAFF GATEKEEPER EN SHOP.HTML
# ==============================================================================
def test_shop_html_contains_inventory_gatekeeper_and_no_admin_button(client):
    """
    Verifica que shop.html no tenga enlaces públicos que mencionen Admin,
    que tenga el botón 'Gestión de Inventario' y el modal 'gatekeeperModal'.
    """
    res = client.get("/static/shop.html")
    assert res.status_code == 200
    html = res.text

    # No debe haber enlace directo público a /admin.html
    assert 'href="/admin.html"' not in html

    # Debe contener el botón estilizado de acceso a inventario
    assert 'id="btnStaffInventoryAccess"' in html
    assert "Gestión de Inventario" in html

    # Debe contener el modal Gatekeeper de staff
    assert 'id="gatekeeperModal"' in html
    assert 'id="gatekeeperForm"' in html
    assert 'id="gatekeeperUser"' in html
    assert 'id="gatekeeperPass"' in html
    assert "Cancelar / Seguir Comprando" in html
    assert "STAFF GATEKEEPER" in html
