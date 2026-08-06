from django.urls import path

from monitoreo import views
from .views import obtener_datos_mapa


urlpatterns = [
    path('',views.home, name="Home"),
    path('agregar',views.agregar, name="Agregar"),
    path('contacto',views.contacto, name="Contacto"),
    path('obtener_datos_mapa/', obtener_datos_mapa, name='obtener_datos_mapa'),

]