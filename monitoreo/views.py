from django.shortcuts import render, HttpResponse
#from monitoreo.forms import formularioAgregar
from django.http import JsonResponse
from monitoreo.models import monitoreo

# Create your views here.

def home(request):

    return render(request, "monitoreo/home.html")


def agregar(request):

    return render(request, "monitoreo/agregar.html")

def contacto(request):

    return render(request, "monitoreo/contacto.html")



#crea una vita para ver los mapas
def obtener_datos_mapa(request):
    datos = monitoreo.objects.values('latitud', 'longitud', 'fecha_monitoreo', 'descripcion', 'monitor', 'lugar', 'tipo_monitoreo', 'usuario_id', 'monitoreo_id', 'plastico_pesca_kg', 'plastico_uso_domestico_kg', 'cuerdas_y_cordeles_kg', 'vidrios_kg', 'latas_kg', 'textil_kg', 'papel_kg', 'neumaticos_kg')
    return JsonResponse(list(datos), safe=False)