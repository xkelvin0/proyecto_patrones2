from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from .models import Curso, Material

@login_required
def crear_anuncio(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar que el usuario es el profesor del curso
    if not hasattr(request.user, 'profesor') or curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para crear anuncios en este curso")
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            titulo = request.POST.get('titulo', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            semana = request.POST.get('semana')
            archivo = request.FILES.get('archivo')
            
            # Validaciones
            if not titulo or not descripcion or not semana:
                messages.error(request, 'Todos los campos obligatorios deben ser completados')
                return redirect('crear_anuncio', curso_id=curso.id)
            
            # Crear el material como anuncio
            material = Material(
                titulo=f"[ANUNCIO] {titulo}",
                descripcion=descripcion,
                curso=curso,
                semana=int(semana),
                archivo=archivo if archivo else None,
                es_anuncio=True,
                fecha_creacion=timezone.now()
            )
            material.save()
            
            messages.success(request, '¡Anuncio publicado exitosamente!')
            return redirect('ver_contenido_curso', curso_id=curso.id)
            
        except Exception as e:
            messages.error(request, f'Error al publicar el anuncio: {str(e)}')
            return redirect('crear_anuncio', curso_id=curso.id)
    
    # Si es GET, mostrar el formulario
    return render(request, 'matriculas/anuncios/crear_anuncio.html', {
        'curso': curso,
        'semanas': range(1, 19),  # Genera números del 1 al 18
    })
