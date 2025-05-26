FROM python:3.10-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    git \
    curl \
    procps \
    lsof \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Clonar el repositorio
RUN git clone https://github.com/CarlosChiguichon/whatsapp-bot.git . \
    && mkdir -p /app/data /app/logs

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Hacer ejecutables los scripts de inicio (si existen)
RUN if [ -f start.sh ]; then chmod +x start.sh; fi

# Exponer el puerto de la aplicación
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["python", "run.py"]