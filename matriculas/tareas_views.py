from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponse, FileResponse, HttpResponseRedirect
from django.db.models import Count, Avg, Case, When, IntegerField, Max, Min
from django.urls import reverse
import os
import xlwt
from datetime import datetime

from .models import Tarea, EntregaTarea, Curso
from .forms import TareaForm, EntregaTareaForm, CalificarTareaForm, EditarTareaForm
from .decorators import profesor_required, estudiante_required

def obtener_estudiante(user):
    if not hasattr(user, 'estudiante'):
        return None
    return user.estudiante

def obtener_profesor(user):
    if not hasattr(user, 'profesor'):
        return None
    return user.profesor

@login_required
@profesor_required
def crear_tarea(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar que el usuario es el profesor del curso
    if curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para crear tareas en este curso")
    
    if request.method == 'POST':
        form = TareaForm(request.POST, request.FILES)
        if form.is_valid():
            tarea = form.save(commit=False)
            tarea.curso = curso
            tarea.save()
            messages.success(request, 'Tarea creada exitosamente')
            return redirect('detalle_curso', curso_id=curso.id)
    else:
        form = TareaForm()
    
    return render(request, 'matriculas/tareas/crear_tarea.html', {
        'form': form,
        'curso': curso,
    })

@login_required
def ver_tarea(request, tarea_id):
    # Obtener la tarea y verificar permisos
    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    # Verificar si el usuario es el profesor del curso o un estudiante matriculado
    es_profesor = hasattr(request.user, 'profesor') and tarea.curso.profesor.user == request.user
    es_estudiante_matriculado = hasattr(request.user, 'estudiante') and \
                              tarea.curso.estudiantes.filter(id=request.user.estudiante.id).exists()
    
    if not (es_profesor or es_estudiante_matriculado):
        return HttpResponseForbidden("No tienes permiso para ver esta tarea")
    
    entrega = None
    form_entrega = None
    
    if hasattr(request.user, 'estudiante'):
        # Vista para estudiantes
        estudiante = request.user.estudiante
        entrega = EntregaTarea.objects.filter(tarea=tarea, estudiante=estudiante).first()
        
        if request.method == 'POST':
            form_entrega = EntregaTareaForm(request.POST, request.FILES, instance=entrega)
            if form_entrega.is_valid():
                nueva_entrega = form_entrega.save(commit=False)
                nueva_entrega.tarea = tarea
                nueva_entrega.estudiante = estudiante
                nueva_entrega.estado = 'P'  # Pendiente de revisión
                nueva_entrega.save()
                messages.success(request, '¡Tarea entregada exitosamente!')
                return redirect('ver_tarea', tarea_id=tarea.id)
        else:
            form_entrega = EntregaTareaForm(instance=entrega)
            
        return render(request, 'matriculas/tareas/ver_tarea_estudiante.html', {
            'tarea': tarea,
            'entrega': entrega,
            'form_entrega': form_entrega,
        })
    
    elif hasattr(request.user, 'profesor'):
        # Vista para profesores
        if tarea.curso.profesor.user != request.user:
            return HttpResponseForbidden("No tienes permiso para ver esta tarea")
            
        entregas = tarea.entregas.all().select_related('estudiante__user')
        
        return render(request, 'matriculas/tareas/ver_tarea_profesor.html', {
            'tarea': tarea,
            'entregas': entregas,
        })
    
    return HttpResponseForbidden("Acceso denegado")

@login_required
@profesor_required
def calificar_entrega(request, entrega_id):
    entrega = get_object_or_404(EntregaTarea, id=entrega_id)
    
    # Verificar que el usuario es el profesor del curso
    if entrega.tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para calificar esta entrega")
    
    if request.method == 'POST':
        form = CalificarTareaForm(request.POST, instance=entrega)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calificación guardada exitosamente')
            return redirect('ver_tarea', tarea_id=entrega.tarea.id)
    else:
        form = CalificarTareaForm(instance=entrega)
    
    return render(request, 'matriculas/tareas/calificar_tarea.html', {
        'form': form,
        'entrega': entrega,
        'tarea': entrega.tarea,
    })

@login_required
def descargar_archivo_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    # Verificar permisos: profesor del curso o estudiante matriculado
    if hasattr(request.user, 'profesor'):
        if tarea.curso.profesor.user != request.user:
            return HttpResponseForbidden("No tienes permiso para descargar este archivo")
    elif hasattr(request.user, 'estudiante'):
        if not tarea.curso.estudiantes.filter(id=request.user.estudiante.id).exists():
            return HttpResponseForbidden("No tienes permiso para descargar este archivo")
    else:
        return HttpResponseForbidden("Acceso denegado")
    
    if not tarea.archivo:
        raise Http404("No hay archivo para descargar")
    
    return FileResponse(tarea.archivo, as_attachment=True)

@login_required
def descargar_entrega(request, entrega_id):
    entrega = get_object_or_404(EntregaTarea, id=entrega_id)
    
    # Verificar permisos: profesor del curso o el estudiante dueño de la entrega
    if hasattr(request.user, 'profesor'):
        if entrega.tarea.curso.profesor.user != request.user:
            return HttpResponseForbidden("No tienes permiso para descargar este archivo")
    elif hasattr(request.user, 'estudiante'):
        if entrega.estudiante.user != request.user:
            return HttpResponseForbidden("No tienes permiso para descargar este archivo")
    else:
        return HttpResponseForbidden("Acceso denegado")
    
    if not entrega.archivo:
        raise Http404("No hay archivo para descargar")
    
    return FileResponse(entrega.archivo, as_attachment=True)

@login_required
@profesor_required
def editar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    if tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para editar esta tarea")
        
    
    # Verificar que el usuario es el profesor del curso
    if tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para editar esta tarea.")
    
    if request.method == 'POST':
        form = EditarTareaForm(request.POST, request.FILES, instance=tarea)
        if form.is_valid():
            tarea = form.save(commit=False)
            # Si se sube un nuevo archivo, eliminar el anterior
            if 'archivo' in request.FILES and tarea.archivo:
                # Eliminar el archivo anterior si existe
                if tarea.archivo and os.path.isfile(tarea.archivo.path):
                    os.remove(tarea.archivo.path)
            tarea.save()
            messages.success(request, 'Tarea actualizada exitosamente')
            return redirect('ver_tarea', tarea_id=tarea.id)
    else:
        form = EditarTareaForm(instance=tarea)
    
    return render(request, 'matriculas/tareas/editar_tarea.html', {
        'form': form,
        'tarea': tarea,
        'curso': tarea.curso,
    })

@login_required
@profesor_required
def exportar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    if tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para exportar esta tarea")
    
    # Obtener todas las entregas de la tarea con información del estudiante
    entregas = tarea.entregas.select_related('estudiante__user').all()
    
    # Crear un libro de trabajo y una hoja de cálculo
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="calificaciones_{tarea.titulo[:30]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Calificaciones')
    
    # Estilos para el encabezado
    header_style = xlwt.easyxf(
        'font: bold on; align: horiz center; borders: left thin, right thin, top thin, bottom thin;'
    )
    
    # Escribir encabezados
    columns = ['Estudiante', 'Email', 'Fecha de entrega', 'Estado', 'Calificación', 'Comentario del estudiante']
    
    for col_num, column_title in enumerate(columns):
        ws.write(0, col_num, column_title, header_style)
        # Ajustar el ancho de la columna
        ws.col(col_num).width = 8000  # Ancho en unidades de 1/256 del ancho del carácter '0'
    
    # Escribir datos
    row_num = 1
    for entrega in entregas:
        ws.write(row_num, 0, f"{entrega.estudiante.user.last_name}, {entrega.estudiante.user.first_name}")
        ws.write(row_num, 1, entrega.estudiante.user.email)
        ws.write(row_num, 2, entrega.fecha_entrega.strftime('%d/%m/%Y %H:%M'))
        ws.write(row_num, 3, entrega.get_estado_display())
        ws.write(row_num, 4, entrega.calificacion or '')
        ws.write(row_num, 5, entrega.comentario_estudiante or '')
        row_num += 1
    
    # Guardar el libro de trabajo en la respuesta
    wb.save(response)
    return response

@login_required
@estudiante_required
def listar_tareas_estudiante(request, curso_id):
    """
    Vista para que un estudiante vea la lista de tareas de un curso.
    Esta vista está en desuso ya que ahora usamos ver_contenido_estudiante.
    Redirige a la nueva vista de contenido del curso.
    """
    return redirect('ver_contenido_estudiante', curso_id=curso_id)

@login_required
@profesor_required
def ver_entrega(request, entrega_id):
    entrega = get_object_or_404(EntregaTarea, id=entrega_id)
    
    # Verificar que el usuario es el estudiante que la entregó o el profesor del curso
    if (request.user != entrega.estudiante.user and 
        (not hasattr(request.user, 'profesor') or 
         request.user.profesor != entrega.tarea.curso.profesor)):
        return HttpResponseForbidden("No tienes permiso para ver esta entrega.")
    
    return render(request, 'matriculas/tareas/ver_entrega.html', {
        'entrega': entrega,
        'tarea': entrega.tarea,  # Add tarea to context
        'estudiante': entrega.estudiante,  # Add estudiante to context
        'es_profesor': hasattr(request.user, 'profesor') and request.user.profesor == entrega.tarea.curso.profesor
    })

@login_required
@profesor_required
def eliminar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    curso_id = tarea.curso.id
    
    # Verificar que el usuario es el profesor del curso
    if tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para eliminar esta tarea.")
    
    if request.method == 'POST':
        # Eliminar la tarea (esto también eliminará las entregas relacionadas por CASCADE)
        tarea.delete()
        messages.success(request, 'La tarea ha sido eliminada correctamente.')
        return redirect('detalle_curso', curso_id=curso_id)
    
    # Si se accede por GET, redirigir a la página de la tarea
    return redirect('ver_tarea', tarea_id=tarea_id)

@login_required
@profesor_required
def ver_estadisticas_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    # Verificar que el usuario es el profesor del curso
    if tarea.curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para ver las estadísticas de esta tarea.")
    
    # Obtener estadísticas de las entregas
    total_estudiantes = tarea.curso.estudiantes.count()
    entregas = tarea.entregas.all()
    total_entregas = entregas.count()
    
    # Calcular porcentaje de entregas
    porcentaje_entregas = (total_entregas / total_estudiantes * 100) if total_estudiantes > 0 else 0
    
    # Calcular estadísticas de calificaciones
    estadisticas = entregas.aggregate(
        promedio=Avg('calificacion'),
        maximo=Max('calificacion'),
        minimo=Min('calificacion'),
        aprobados=Count(
            Case(
                When(calificacion__gte=10.5, then=1),  # Aprobado con 10.5 o más
                output_field=IntegerField(),
            )
        ),
        desaprobados=Count(
            Case(
                When(calificacion__lt=10.5, then=1),  # Desaprobado con menos de 10.5
                output_field=IntegerField(),
            )
        ),
    )
    
    # Obtener el rango de fechas de entrega
    fechas_entrega = entregas.aggregate(
        primera_entrega=Min('fecha_entrega'),
        ultima_entrega=Max('fecha_entrega')
    )
    
    # Preparar datos para el gráfico de distribución de calificaciones
    # Agrupar calificaciones en rangos (0-5, 6-10, 11-15, 16-20)
    rangos_calificaciones = [
        {'rango': '0-5', 'cantidad': entregas.filter(calificacion__gte=0, calificacion__lte=5).count()},
        {'rango': '6-10', 'cantidad': entregas.filter(calificacion__gt=5, calificacion__lte=10).count()},
        {'rango': '11-15', 'cantidad': entregas.filter(calificacion__gt=10, calificacion__lte=15).count()},
        {'rango': '16-20', 'cantidad': entregas.filter(calificacion__gt=15, calificacion__lte=20).count()},
    ]
    
    # Obtener las últimas 5 entregas
    ultimas_entregas = entregas.select_related('estudiante__user').order_by('-fecha_entrega')[:5]
    
    return render(request, 'matriculas/tareas/estadisticas_tarea.html', {
        'tarea': tarea,
        'total_estudiantes': total_estudiantes,
        'total_entregas': total_entregas,
        'porcentaje_entregas': round(porcentaje_entregas, 2),
        'estadisticas': estadisticas,
        'fechas_entrega': fechas_entrega,
        'rangos_calificaciones': rangos_calificaciones,
        'ultimas_entregas': ultimas_entregas,
    })
