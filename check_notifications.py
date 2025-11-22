import os
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_matriculas_django.settings')
django.setup()

from matriculas.models import Notificacion

# Buscar notificaciones con URL que contenga 'cursos/'
notificaciones_problematicas = Notificacion.objects.filter(url__contains='cursos/')

print(f"Se encontraron {notificaciones_problematicas.count()} notificaciones con URL que contiene 'cursos/'")

for notif in notificaciones_problematicas:
    print(f"ID: {notif.id}, URL: {notif.url}, Título: {notif.titulo}")
    # Extraer el ID del curso de la URL antigua
    curso_id = notif.url.strip('/').split('/')[-1]
    # Actualizar la URL a la ruta correcta del contenido del curso
    notif.url = f"/profesor/curso/{curso_id}/contenido/"
    notif.save()
    print(f"URL actualizada a: {notif.url}")

print("Proceso completado.")
