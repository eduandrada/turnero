"""
app/core/path_security.py - Prevención centralizada de Path Traversal y manejo seguro de rutas.
"""
import os
import re
from typing import Optional
from fastapi import HTTPException

# Caracteres peligrosos para nombres de archivo
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo extrayendo únicamente el nombre base
    y eliminando caracteres peligrosos o secuencias de escape.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="El nombre de archivo no puede estar vacío.")
    
    # Extraer solo el componente basename (elimina ../, /etc/passwd, C:\...)
    base_name = os.path.basename(filename.strip().replace("\\", "/"))
    # Remover caracteres inválidos
    clean_name = INVALID_FILENAME_CHARS.sub("_", base_name).strip()
    
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido o peligroso.")
        
    return clean_name

def safe_path(base_dir: str, user_filename: str) -> str:
    """
    Verifica de forma estricta que la ruta resultante resida dentro de base_dir.
    Previene de forma determinista cualquier intento de Path Traversal (../, rutas absolutas, etc.).
    """
    if not user_filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no provisto.")

    # 1. Rechazar explícitamente secuencias comunes de path traversal
    norm_input = user_filename.replace("\\", "/")
    if "../" in norm_input or norm_input.startswith("/") or re.match(r'^[a-zA-Z]:', norm_input):
        raise HTTPException(
            status_code=400,
            detail="Intento de Path Traversal detectado: no se permiten rutas relativas ni absolutas."
        )

    clean_file = sanitize_filename(user_filename)
    abs_base = os.path.abspath(base_dir)
    full_path = os.path.abspath(os.path.join(abs_base, clean_file))

    # 2. Verificación estricta mediante commonpath
    try:
        common = os.path.commonpath([full_path, abs_base])
    except ValueError:
        raise HTTPException(status_code=400, detail="Acceso denegado: ruta fuera del directorio permitido.")

    if common != abs_base:
        raise HTTPException(
            status_code=400, 
            detail="Acceso denegado: la ruta calculada está fuera del directorio autorizado."
        )

    return full_path
