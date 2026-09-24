# ==========================================
# BLADESYNC AI 2026 - PRODUCTION DOCKERFILE
# ==========================================
FROM python:3.11-slim

# Evitar escritura de bytecode y habilitar salida en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY app/ ./app/
COPY .env.example .env

# Exponer el puerto del servicio
EXPOSE 8000

# Healthcheck para garantizar alta disponibilidad
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/services || exit 1

# Comando de inicio del servidor ASGI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
