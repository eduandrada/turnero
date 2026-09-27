"""
app/utils.py - Utilidades centrales de BladeSync AI:
1. Normalización y validación de números telefónicos (Argentina / Internacional).
2. Procesador fonético y normalización de códigos de turno para Web Speech API.
3. Motor de plantillas y estilos de locución para Pantalla TV / Digital Signage.
"""

import re
from typing import Optional

# Mapeo de números en español para fonética de turnos (0 a 999)
UNIDADES = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"
]

DECENAS = [
    "", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"
]

CENTENAS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
    "seiscientos", "setecientos", "ochocientos", "novecientos"
]

def number_to_words_es(n: int) -> str:
    """Convierte un número entero (0 a 999) a su expresión fonética natural en español."""
    if n < 0 or n > 999:
        return str(n)
    if n == 100:
        return "cien"
    if n < 30:
        return UNIDADES[n]
    if n < 100:
        dec = n // 10
        uni = n % 10
        if uni == 0:
            return DECENAS[dec]
        return f"{DECENAS[dec]} y {UNIDADES[uni]}"
    
    cen = n // 100
    resto = n % 100
    if resto == 0:
        return CENTENAS[cen]
    return f"{CENTENAS[cen]} {number_to_words_es(resto)}"


def normalize_phone(phone: str) -> str:
    """
    Normaliza y valida un número telefónico garantizando compatibilidad con formato internacional E.164 y WhatsApp.
    Acepta formatos argentinos (+54, 54, 9, 15, 0, espacios, guiones) e internacionales.
    Ejemplos:
      '03834 15123456' -> '+5493834123456'
      '+54 9 3834 12-3456' -> '+5493834123456'
      '+543834123456' -> '+5493834123456'
      '3834123456' -> '+5493834123456'
      '+34 612 34 56 78' -> '+34612345678'
    """
    if not phone:
        return ""
    
    raw = "".join(filter(str.isdigit, str(phone)))
    if not raw:
        return ""

    # Remover prefijo internacional 00 si vino como 0054... o 0034...
    if raw.startswith("00"):
        raw = raw[2:]

    # Si es número de otro país (no empieza con 54, no empieza con 0, y el original tenía +)
    if str(phone).strip().startswith("+") and not raw.startswith("54"):
        return f"+{raw}"

    # Argentina:
    # Si empieza con 54:
    if raw.startswith("54"):
        rest = raw[2:]
        if rest.startswith("9"):
            rest = rest[1:]
        # Verificar si rest tiene un 15 después del código de área (ej: 3834 15 123456)
        for area_len in (2, 3, 4):
            if len(rest) > area_len + 2 and rest[area_len:area_len+2] == "15":
                rest = rest[:area_len] + rest[area_len+2:]
                break
        return f"+549{rest}"

    # Si empieza con 0 (discado nacional):
    if raw.startswith("0"):
        rest = raw[1:]
        # Buscar 15 después del área
        for area_len in (2, 3, 4):
            if len(rest) > area_len + 2 and rest[area_len:area_len+2] == "15":
                rest = rest[:area_len] + rest[area_len+2:]
                break
        return f"+549{rest}"

    # Si empieza con 15 (móvil sin código de área, asume Catamarca 3834):
    if raw.startswith("15") and len(raw) == 8:
        return f"+5493834{raw[2:]}"

    # Si tiene 10 dígitos (área + abonado, ej: 3834123456 o 1145678901):
    if len(raw) == 10:
        return f"+549{raw}"

    # Si tiene más de 10 dígitos y tiene 15 intermedio
    for area_len in (2, 3, 4):
        if len(raw) > area_len + 2 and raw[area_len:area_len+2] == "15":
            cleaned = raw[:area_len] + raw[area_len+2:]
            return f"+549{cleaned}"

    return f"+{raw}"


def format_turn_for_speech(turn_code: str) -> str:
    """
    Normaliza y convierte un código de turno a lenguaje fonético fluido para Web Speech API.
    Evita lecturas robóticas como 'B guión cero ocho'.
    Ejemplos:
      - 'A-125' o 'A125' -> 'A ciento veinticinco'
      - 'B-08' o 'B08'   -> 'B ocho'
      - 'BAR-025'        -> 'B A R veinticinco'
      - '045'            -> 'cuarenta y cinco'
      - 'T-102'          -> 'T ciento dos'
    """
    if not turn_code:
        return ""

    cleaned = str(turn_code).strip().upper()
    # Separar letras y números
    match = re.match(r"^([A-Z]*)[-_/\s]*(\d+)$", cleaned)
    if match:
        letters, number_str = match.groups()
        num_val = int(number_str)
        num_words = number_to_words_es(num_val)

        if not letters:
            return num_words

        # Deletrear las letras de forma espaciada (ej: 'B A R' o 'A')
        letters_spaced = " ".join(list(letters))
        return f"{letters_spaced} {num_words}"

    # Si no coincide con el patrón habitual, remover caracteres técnicos como guiones
    sanitized = re.sub(r"[-_/\\]", " ", cleaned)
    return sanitized


def build_speech_announcement(
    template_style: str = "moderno",
    turn_code: str = "",
    client_name: str = "",
    barber_name: str = "",
    station: str = "",
    service: str = "",
    custom_template: str = "",
    style: Optional[str] = None,
    station_name: Optional[str] = None,
    service_name: Optional[str] = None
) -> str:
    """
    Construye la locución sintetizada para la pantalla TV según el estilo configurado.
    Aplica fallback sintáctico limpio si faltan variables opcionales (barbero, puesto, cliente).
    """
    phonetic_turn = format_turn_for_speech(turn_code)
    style = (style or template_style or "moderno").lower().strip()
    station = station_name or station or ""
    service = service_name or service or ""

    # Si se especificó una plantilla personalizada
    if custom_template and "{turno}" in custom_template:
        t = custom_template.replace("{turno}", phonetic_turn)
        if barber_name:
            t = t.replace("{barbero}", barber_name)
        else:
            t = re.sub(r"\s*(con|hacia|del?)\s*\{barbero\}", "", t)
            t = t.replace("{barbero}", "")

        if client_name:
            t = t.replace("{cliente}", client_name)
        else:
            t = t.replace("{cliente}", "")

        if station:
            t = t.replace("{puesto}", station)
        else:
            t = re.sub(r"\s*(al|en el)\s*\{puesto\}", "al sillón disponible", t)
            t = t.replace("{puesto}", "")

        if service:
            t = t.replace("{servicio}", service)
        else:
            t = t.replace("{servicio}", "")
        return re.sub(r"\s+", " ", t).strip()

    # Presets nativos con concordancia gramatical:
    if style == "minimal":
        return f"{phonetic_turn}, tu turno."

    if style == "urbano":
        if barber_name:
            return f"Atento {phonetic_turn}, ya podés pasar con {barber_name}."
        return f"Atento {phonetic_turn}, ya podés pasar a tu atención."

    if style == "clasico":
        if barber_name:
            return f"Turno {phonetic_turn}, por favor dirigirse al puesto de {barber_name}."
        return f"Turno {phonetic_turn}, por favor dirigirse al sillón de atención."

    if style == "puesto":
        target_station = station or (f"puesto de {barber_name}" if barber_name else "sillón disponible")
        return f"Turno {phonetic_turn}, por favor pasar al {target_station}."

    # Por defecto: "moderno"
    if barber_name:
        return f"Turno {phonetic_turn}, te esperamos con {barber_name}."
    return f"Turno {phonetic_turn}, te esperamos para tu atención."
