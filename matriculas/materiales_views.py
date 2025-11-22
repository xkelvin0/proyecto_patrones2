from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from .models import Curso, Material

@login_required
def subir_material(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar que el usuario es el profesor del curso
    if not hasattr(request.user, 'profesor') or curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para subir material a este curso")
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            titulo = request.POST.get('titulo', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            semana = request.POST.get('semana')
            archivo = request.FILES.get('archivo')
            enlace = request.POST.get('enlace', '').strip()
            
            # Validaciones básicas
            if not titulo:
                messages.error(request, 'El título es obligatorio')
                return redirect('subir_material', curso_id=curso.id)
                
            if not semana:
                messages.error(request, 'Debes seleccionar una semana')
                return redirect('subir_material', curso_id=curso.id)
                
            if not archivo and not enlace:
                messages.error(request, 'Debes subir un archivo o proporcionar un enlace')
                return redirect('subir_material', curso_id=curso.id)
            
            # Crear el material
            material = Material(
                titulo=titulo,
                descripcion=descripcion,
                curso=curso,
                semana=int(semana),
                archivo=archivo if archivo else None,
                enlace=enlace if enlace else None,
                fecha_creacion=timezone.now()
            )
            material.save()
            
            messages.success(request, '¡Material subido exitosamente!')
            return redirect('ver_contenido_curso', curso_id=curso.id)
            
        except Exception as e:
            messages.error(request, f'Error al subir el material: {str(e)}')
            return redirect('subir_material', curso_id=curso.id)
    
    # Si es GET, mostrar el formulario
    return render(request, 'matriculas/subir_material_simple.html', {
        'curso': curso,
    })
