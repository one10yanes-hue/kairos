# Dockerfile — Kairos en producción con Waitress
# Imagen base: Python 3.10 sobre Debian (para instalar ODBC Driver 17)
FROM python:3.10-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# Instalar dependencias del sistema + ODBC Driver 17 para SQL Server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    unixodbc-dev \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl -sSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para ejecutar la app
RUN groupadd -r kairos && useradd -r -g kairos -d /app kairos

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt waitress

# Copiar código del proyecto
COPY . .

# Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput

# Crear directorios necesarios
RUN mkdir -p /app/media /app/staticfiles && chown -R kairos:kairos /app

# Cambiar a usuario no-root
USER kairos

# Puerto
EXPOSE 8000

# Entrypoint: migrar + iniciar Waitress
CMD python manage.py migrate --noinput && \
    waitress-serve --host=0.0.0.0 --port=8000 --threads=8 config.wsgi:application
