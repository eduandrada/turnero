"""
tests/test_public_settings.py - Pruebas para FASE 12 (Configuración pública segura y estricta).
Verifica que /api/public/settings devuelva únicamente datos de branding y visuales públicos,
y JAMÁS exponga tokens, contraseñas, secretos ni API keys.
"""
import pytest

def test_public_settings_whitelist(client):
    """Verifica que /api/public/settings devuelva atributos públicos válidos."""
    res = client.get("/api/public/settings")
    assert res.status_code == 200
    data = res.json()

    assert "barber_name" in data
    assert "app_name" in data

def test_public_settings_never_expose_sensitive_keys(client):
    """
    CRITERIO ESTRICTO DE SEGURIDAD:
    Comprobar que en la respuesta de /api/public/settings no figure NINGÚN dato sensible:
    - secret
    - token
    - password
    - api_key
    - app_secret
    - whatsapp_access_token
    - etc.
    """
    res = client.get("/api/public/settings")
    assert res.status_code == 200
    data = res.json()

    forbidden_substrings = [
        "secret",
        "token",
        "password",
        "api_key",
        "app_secret",
        "access_token",
        "private",
        "hash"
    ]

    all_keys = list(data.keys())
    all_values_str = " ".join([str(v) for v in data.values()])

    for key in all_keys:
        lower_key = key.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lower_key, (
                f"¡ALERTA DE SEGURIDAD! La clave '{key}' en /api/public/settings "
                f"contiene un término sensible prohibido: '{forbidden}'"
            )

    # También verificar que el token de prueba guardado en BD ('EAAB_TEST_SECRET_TOKEN_DO_NOT_LEAK') no aparezca en los valores
    assert "EAAB_TEST_SECRET_TOKEN_DO_NOT_LEAK" not in all_values_str, (
        "¡Fuga crítica de secretos! El token de WhatsApp se encontró en la respuesta pública."
    )
