from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Curso, Notificacion, Tarea, EntregaTarea

@receiver(post_save, sender=Curso)
def crear_notificacion_curso(sender, instance, created, **kwargs):
    """
    Crea una notificación cuando se asigna un nuevo curso a un profesor.
    """
    if created and instance.profesor and instance.profesor.user:
        Notificacion.objects.create(
            usuario=instance.profesor.user,
            titulo=f"Nuevo curso asignado: {instance.nombre}",
            mensaje=f"Se te ha asignado el curso {instance.codigo} - {instance.nombre}.",
            tipo='curso',
            curso=instance,
            url=f"/profesor/curso/{instance.id}/contenido/"  # URL corregida para ver el contenido del curso
        )

@receiver(post_save, sender=Tarea)
def crear_notificacion_tarea(sender, instance, created, **kwargs):
    """
    Crea notificaciones cuando se crea una nueva tarea en un curso.
    """
    if created:
        # Notificar al profesor
        if instance.curso.profesor.user:
            Notificacion.objects.create(
                usuario=instance.curso.profesor.user,
                titulo=f"Nueva tarea creada: {instance.titulo}",
                mensaje=f"Has creado la tarea '{instance.titulo}' para el curso {instance.curso.nombre}.",
                tipo='tarea',
                curso=instance.curso,
                tarea=instance,
                url=f"/profesor/"  # Cambiado a la página del profesor donde se listan las tareas
            )
        
        # Notificar a los estudiantes matriculados
        for matricula in instance.curso.matriculas.filter(estado='A'):
            if matricula.estudiante.user:
                Notificacion.objects.create(
                    usuario=matricula.estudiante.user,
                    titulo=f"Nueva tarea: {instance.titulo}",
                    mensaje=f"Se ha publicado una nueva tarea en el curso {instance.curso.nombre}: {instance.titulo}.",
                    tipo='tarea',
                    curso=instance.curso,
                    tarea=instance,
                    url=f"/profesor/"  # Cambiado a la página del profesor donde se listan las tareas
                )

@receiver(post_save, sender=EntregaTarea)
def crear_notificacion_entrega_tarea(sender, instance, created, **kwargs):
    """
    Crea notificaciones cuando un estudiante entrega una tarea.
    """
    if created and instance.tarea.curso.profesor.user:
        Notificacion.objects.create(
            usuario=instance.tarea.curso.profesor.user,
            titulo=f"Nueva entrega de tarea: {instance.tarea.titulo}",
            mensaje=f"{instance.estudiante.user.get_full_name()} ha entregado la tarea '{instance.tarea.titulo}'.",
            tipo='tarea',
            curso=instance.tarea.curso,
            tarea=instance.tarea,
            url=f"/profesor/"  # Cambiado a la página del profesor donde se listan las entregas
        )

@receiver(pre_delete, sender=Curso)
def eliminar_notificaciones_curso(sender, instance, **kwargs):
    """
    Elimina todas las notificaciones relacionadas con un curso cuando este se elimina.
    """
    # Eliminar notificaciones relacionadas con el curso
    Notificacion.objects.filter(curso=instance).delete()
    
    # Si hay tareas asociadas, también eliminamos sus notificaciones
    tareas_del_curso = Tarea.objects.filter(curso=instance)
    for tarea in tareas_del_curso:
        Notificacion.objects.filter(tarea=tarea).delete()
