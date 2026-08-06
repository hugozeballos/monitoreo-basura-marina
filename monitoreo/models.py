from django.db import models

# Create your models here.

class monitoreo(models.Model):
    latitud=models.DecimalField(max_digits=10, decimal_places=7, null=True,blank=True)
    longitud=models.DecimalField(max_digits=10, decimal_places=7, null=True,blank=True)
    fecha_monitoreo = models.DateField(null=True,blank=True)
    descripcion = models.CharField(max_length=50,blank=True)
    monitor = models.CharField(max_length=50,blank=True)
    lugar = models.CharField(max_length=50,blank=True)
    tipo_monitoreo = models.CharField(max_length=50,blank=True)
    usuario_id = models.CharField(max_length=50,blank=True)
    monitoreo_id = models.CharField(max_length=50,blank=True)
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now_add=True)
    plastico_pesca_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    plastico_uso_domestico_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    cuerdas_y_cordeles_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    vidrios_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    latas_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    textil_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    papel_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    neumaticos_kg = models.DecimalField(max_digits=5, decimal_places=2,null=True)
    id_indicadores_kg = models.CharField(max_length=3,blank=True)
    plastico_pesca_un = models.IntegerField(null=True)
    plastico_uso_domestico_un = models.IntegerField(null=True)
    cuerdas_y_cordeles_un = models.IntegerField(null=True)
    vidrios_un = models.IntegerField(null=True)
    latas_un = models.IntegerField(null=True)
    textil_un = models.IntegerField(null=True)
    papel_un = models.IntegerField(null=True)
    neumaticos_un = models.IntegerField(null=True)
    id_indicadores_un = models.CharField(max_length=3,blank=True)
    


class usuarios(models.Model):
    fecha_registro=models.DateField(null=True)
    apellido = models.CharField(max_length=50,blank=True)
    contacto = models.CharField(max_length=50,blank=True)
    correo = models.CharField(max_length=50,blank=True)
    identificacion = models.CharField(max_length=50,blank=True)
    nombre = models.CharField(max_length=50,blank=True)
    passsword = models.CharField(max_length=50,blank=True)
    rol = models.CharField(max_length=50,blank=True)
    usuario = models.CharField(max_length=50,blank=True)
    usuario_id = models.CharField(max_length=50,blank=True)
