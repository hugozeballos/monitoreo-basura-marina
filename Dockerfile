# Imagen base ligera
FROM python:3.12-slim

# Evita generación de archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (mejor cache Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Puerto que Cloud Run usa
ENV PORT 8080

# Comando de producción
CMD ["gunicorn", "monitoreoBasuraMarina.wsgi:application", "--bind", "0.0.0.0:8080"]
