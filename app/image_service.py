import os
import io
import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageOps

logger = logging.getLogger("bladesync.images")

# Configuración del motor de subida
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
VALID_CONTEXTS = {"avatar", "product", "branding"}

UPLOAD_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "uploads"))

CONTEXT_SUBDIRS = {
    "avatar": "avatars",
    "product": "products",
    "branding": "branding"
}

# Inicializar carpetas de almacenamiento si no existen
for sub in CONTEXT_SUBDIRS.values():
    os.makedirs(os.path.join(UPLOAD_BASE_DIR, sub), exist_ok=True)


class ImageProcessingError(Exception):
    """Excepción específica para errores de validación o procesamiento de imágenes."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_image_payload(file_bytes: bytes, filename: str, context: str) -> None:
    """
    Valida tamaño, extensión y cabeceras reales del archivo (MIME/Magic check con Pillow).
    """
    if context not in VALID_CONTEXTS:
        raise ImageProcessingError(
            f"Contexto inválido '{context}'. Permitidos: {list(VALID_CONTEXTS)}", 
            status_code=400
        )

    if not filename:
        raise ImageProcessingError("Nombre de archivo no especificado.", status_code=400)

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageProcessingError(
            f"Extensión no permitida ('{ext}'). Formatos válidos: {list(ALLOWED_EXTENSIONS)}",
            status_code=400
        )

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise ImageProcessingError(
            f"El archivo excede el tamaño máximo permitido de 5 MB (Tamaño actual: {size_mb:.2f} MB).",
            status_code=400
        )

    if len(file_bytes) == 0:
        raise ImageProcessingError("El archivo recibido está vacío.", status_code=400)

    # Validar cabeceras reales de la imagen usando Pillow verify()
    try:
        with Image.open(io.BytesIO(file_bytes)) as probe:
            probe.verify()
            detected_format = probe.format
            if detected_format not in ALLOWED_FORMATS:
                raise ImageProcessingError(
                    f"Formato interno de imagen no admitido ('{detected_format}'). "
                    f"Formatos permitidos: {list(ALLOWED_FORMATS)}",
                    status_code=400
                )
    except Exception as e:
        if isinstance(e, ImageProcessingError):
            raise e
        logger.warning(f"Falla de verificación en cabeceras de imagen: {e}")
        raise ImageProcessingError(
            "El archivo contiene bytes corruptos o no corresponde a una imagen válida.",
            status_code=400
        )


def _prepare_color_mode(img: Image.Image) -> Image.Image:
    """
    Preserva el canal alfa (transparencia) si existe, o convierte a RGB estándar.
    WebP soporta nativamente RGBA.
    """
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        return img.convert("RGBA")
    return img.convert("RGB")


def process_and_save_image(
    file_bytes: bytes,
    original_filename: str,
    context: str,
    previous_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pipeline de procesamiento universal con Pillow:
    1. Valida extensión, tamaño y cabeceras reales.
    2. Corrige orientación EXIF automática.
    3. Redimensiona y optimiza según contexto:
       - 'avatar': 300x300 px centrado (recorte inteligente cuadrado).
       - 'product': max 800x800 px manteniendo relación de aspecto.
       - 'branding': max 600 px de ancho manteniendo proporciones.
    4. Convierte y comprime a WebP al 85% de calidad.
    5. Guarda con nombre UUID v4 no colisionable.
    6. Opcionalmente borra el archivo previo si se provee previous_url.
    """
    validate_image_payload(file_bytes, original_filename, context)

    subdir = CONTEXT_SUBDIRS[context]
    target_dir = os.path.join(UPLOAD_BASE_DIR, subdir)

    try:
        # Abrir imagen para procesamiento
        img = Image.open(io.BytesIO(file_bytes))

        # Corrección de orientación EXIF (típica en fotos de smartphones)
        img = ImageOps.exif_transpose(img)
        img = _prepare_color_mode(img)

        width, height = img.size

        # Transformación según contexto
        if context == "avatar":
            # Recorte centrado a cuadrado y redimensionado a 300x300
            img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        elif context == "product":
            # Mantener relación de aspecto dentro de caja de 800x800
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        elif context == "branding":
            # Máximo 600 px de ancho manteniendo proporciones
            if width > 600:
                new_height = max(1, int(height * (600 / width)))
                img = img.resize((600, new_height), Image.Resampling.LANCZOS)

        # Generar nombre único UUID v4
        unique_id = uuid.uuid4().hex
        final_filename = f"{unique_id}.webp"
        final_filepath = os.path.join(target_dir, final_filename)

        # Guardar en formato WebP optimizado
        img.save(final_filepath, format="WEBP", quality=85, method=6)
        final_size_bytes = os.path.getsize(final_filepath)
        out_width, out_height = img.size

        public_url = f"/static/uploads/{subdir}/{final_filename}"

        # Limpieza de archivo huérfano anterior si se especifica
        if previous_url:
            delete_orphan_file(previous_url)

        logger.info(
            f"Imagen procesada exitosamente [{context}]: {public_url} "
            f"({out_width}x{out_height} px, {final_size_bytes} bytes)"
        )

        return {
            "status": "success",
            "url": public_url,
            "filename": final_filename,
            "context": context,
            "width": out_width,
            "height": out_height,
            "size_bytes": final_size_bytes
        }

    except Exception as e:
        if isinstance(e, ImageProcessingError):
            raise e
        logger.exception(f"Error procesando imagen para contexto {context}: {e}")
        raise ImageProcessingError(f"Error en el motor de procesamiento de imagen: {str(e)}", status_code=500)


def delete_orphan_file(file_url_or_path: Optional[str]) -> bool:
    """
    Elimina de forma segura un archivo huérfano dentro de static/uploads/.
    Previene vulnerabilidades de Path Traversal validando la ruta canónica.
    """
    if not file_url_or_path:
        return False

    try:
        cleaned_path = file_url_or_path.split("?")[0].strip()
        # Normalizar si viene como URL pública /static/uploads/...
        if cleaned_path.startswith("/static/uploads/"):
            rel_part = cleaned_path[len("/static/uploads/"):]
            full_path = os.path.abspath(os.path.join(UPLOAD_BASE_DIR, rel_part))
        elif cleaned_path.startswith("static/uploads/"):
            rel_part = cleaned_path[len("static/uploads/"):]
            full_path = os.path.abspath(os.path.join(UPLOAD_BASE_DIR, rel_part))
        elif os.path.isabs(cleaned_path):
            full_path = os.path.abspath(cleaned_path)
        else:
            full_path = os.path.abspath(os.path.join(UPLOAD_BASE_DIR, cleaned_path))

        # Verificación estricta de seguridad contra Path Traversal:
        # La ruta canónica debe estar estrictamente dentro de UPLOAD_BASE_DIR
        common = os.path.commonpath([full_path, UPLOAD_BASE_DIR])
        if common != UPLOAD_BASE_DIR:
            logger.warning(f"Seguridad: Intento de borrado de archivo fuera del directorio seguro: {file_url_or_path}")
            return False

        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)
            logger.info(f"Archivo huérfano eliminado correctamente: {full_path}")
            return True
        return False
    except Exception as e:
        logger.warning(f"No se pudo eliminar el archivo huérfano '{file_url_or_path}': {e}")
        return False
