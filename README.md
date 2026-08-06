# Marine Litter Monitoring Platform (Sistema de Monitoreo de Basura Marina)

Plataforma Django que digitaliza el proceso científico de muestreo de basura marina en playas.

## Qué problema resuelve

Los programas de ciencia ciudadana que monitorean residuos marinos suelen depender de planillas sueltas y CSV heterogéneos para registrar sus muestreos, lo que dificulta consolidar datos comparables entre playas, países y organizaciones. Este proyecto reemplaza eso por un flujo estructurado:

- Registra playas y define métodos de muestreo (ej. grilla de transectos × estaciones).
- Genera automáticamente las unidades de muestreo esperadas según el método elegido.
- Permite cargar conteos de residuos por tipo (plásticos, colillas, vidrio, metales, etc.) por unidad.
- Aplica un flujo de validación (`borrador → enviado → validado / rechazado`) antes de que un dato entre a las visualizaciones públicas, evitando que datos incompletos o sin revisar se muestren como oficiales.
- Expone los datos vía una API propia y los visualiza en un mapa interactivo con gráficos de composición por playa, por transecto/estación y por país.
- Incluye importación de datos reales desde CSV con formatos problemáticos (separador `;`, codificación con BOM, decimales con coma, fechas mixtas, valores faltantes) mediante comandos de management personalizados.

## Stack técnico

- **Backend:** Python, Django 4.2, PostgreSQL (Cloud SQL en producción, SQLite en desarrollo local)
- **Servidor / despliegue:** Gunicorn, WhiteNoise (archivos estáticos), Docker, Google Cloud Run
- **Frontend:** Leaflet.js (mapa interactivo), Chart.js (gráficos de composición, densidad por transecto/estación), HTML + JS vanilla
- **Otros:** django-formtools (wizard multi-paso para creación de eventos de muestreo), python-dotenv, psycopg2

## Cómo correrlo (desarrollo local)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Configurar variables de entorno (ver monitoreoBasuraMarina/settings.py
# para las variables esperadas: DEBUG, DB_NAME, DB_USER, DB_PASSWORD, etc.)

python manage.py migrate
python manage.py create_admin              # crea un superusuario por defecto
python manage.py import_beach_macrolitter datos/datos.csv   # opcional: carga datos de ejemplo
python manage.py runserver
```

## Estado actual

El deploy en Google Cloud Run fue dado de baja: la plataforma cubría capacidades más completas de las que el proyecto necesitaba en esa etapa, y su costo de mantenimiento no se justificaba frente a una alternativa más liviana orientada solo a visualización pública. Esa versión liviana es [marine-litter-monitor](https://hugozeballos.github.io/marine-litter-monitor/), también de este autor.

Este repositorio se mantiene como el sistema completo de backend/gestión (carga de datos, validación, administración), con el modelo de datos y el flujo de trabajo científico implementados y funcionando.
