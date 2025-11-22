import logging
from functools import wraps
import csv
import xlwt
from django.http import HttpResponse
from .models import Curso, Estudiante, Profesor, Matricula, Tarea, EntregaTarea, Notificacion
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Sum
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.views import LoginView as AuthLoginView
from .models import Estudiante, Profesor, Curso, Matricula
from .forms import (RegistroEstudianteForm, RegistroProfesorForm, RegistroUsuarioForm, 
                   CursoForm, MatriculaForm, EditarPerfilUsuarioForm, 
                   EditarPerfilEstudianteForm, EditarPerfilProfesorForm)

# Decoradores personalizados
def estudiante_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'estudiante'):
            return HttpResponseForbidden("Acceso denegado: Se requiere ser estudiante")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def profesor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'profesor'):
            return HttpResponseForbidden("Acceso denegado: Se requiere ser profesor")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Configuración del logger
logger = logging.getLogger(__name__)

def es_estudiante(user):
    return hasattr(user, 'estudiante')

def es_profesor(user):
    return hasattr(user, 'profesor')

def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin:index')
        elif hasattr(request.user, 'estudiante'):
            return redirect('dashboard_estudiante')
        elif hasattr(request.user, 'profesor'):
            return redirect('dashboard_profesor')
    return render(request, 'matriculas/index.html')

class CustomLoginView(AuthLoginView):
    template_name = 'matriculas/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if hasattr(user, 'estudiante'):
            return reverse('dashboard_estudiante')
        elif hasattr(user, 'profesor'):
            return reverse('dashboard_profesor')
        elif user.is_superuser:
            return reverse('admin:index')
        return reverse('index')

    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos')
        return super().form_invalid(form)

# Vista de login que usa la clase CustomLoginView
@csrf_exempt
def login_view(request):
    return CustomLoginView.as_view()(request)

def logout_view(request):
    logout(request)
    return redirect('index')

def registro_estudiante(request):
    if request.method == 'POST':
        user_form = RegistroUsuarioForm(request.POST)
        estudiante_form = RegistroEstudianteForm(request.POST, request.FILES)
        
        if user_form.is_valid() and estudiante_form.is_valid():
            # Guardar el usuario con el correo electrónico
            user = user_form.save(commit=False)
            user.email = user_form.cleaned_data['email']
            user.first_name = user_form.cleaned_data['first_name']
            user.last_name = user_form.cleaned_data['last_name']
            user.save()
            
            # Guardar el perfil de estudiante
            estudiante = estudiante_form.save(commit=False)
            estudiante.user = user
            estudiante.save()
            
            # Iniciar sesión automáticamente
            login(request, user)
            messages.success(request, '¡Registro exitoso! Ahora estás registrado como estudiante.')
            return redirect('dashboard_estudiante')
        else:
            # Si hay errores, mostrarlos al usuario
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {user_form.fields[field].label}: {error}')
            
            for field, errors in estudiante_form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {estudiante_form.fields[field].label}: {error}')
    else:
        user_form = RegistroUsuarioForm()
        estudiante_form = RegistroEstudianteForm()
    
    return render(request, 'matriculas/registro_estudiante.html', {
        'user_form': user_form,
        'estudiante_form': estudiante_form,
        'title': 'Registro de Estudiante'
    })

def registro_profesor(request):
    if request.method == 'POST':
        user_form = RegistroUsuarioForm(request.POST)
        profesor_form = RegistroProfesorForm(request.POST, request.FILES)
        
        if user_form.is_valid() and profesor_form.is_valid():
            # Guardar el usuario con el correo electrónico
            user = user_form.save(commit=False)
            user.email = user_form.cleaned_data['email']
            user.first_name = user_form.cleaned_data['first_name']
            user.last_name = user_form.cleaned_data['last_name']
            user.is_staff = True
            user.save()
            
            # Guardar el perfil de profesor
            profesor = profesor_form.save(commit=False)
            profesor.user = user
            profesor.save()
            
            # Iniciar sesión automáticamente
            login(request, user)
            messages.success(request, '¡Registro exitoso! Ahora estás registrado como profesor.')
            return redirect('dashboard_profesor')
        else:
            # Si hay errores, mostrarlos al usuario
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {user_form.fields[field].label}: {error}')
            
            for field, errors in profesor_form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {profesor_form.fields[field].label}: {error}')
    else:
        user_form = RegistroUsuarioForm()
        profesor_form = RegistroProfesorForm()
    
    return render(request, 'matriculas/registro_profesor.html', {
        'user_form': user_form,
        'profesor_form': profesor_form,
        'title': 'Registro de Profesor'
    })

@login_required
@estudiante_required
def dashboard_estudiante(request):
    
    estudiante = request.user.estudiante
    matriculas = Matricula.objects.filter(estudiante=estudiante).select_related('curso')
    cursos_disponibles = Curso.objects.exclude(
        id__in=matriculas.values_list('curso_id', flat=True)
    )
    
    # Obtener notificaciones no leídas
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).order_by('-fecha_creacion')[:10]
    
    return render(request, 'matriculas/dashboard_estudiante.html', {
        'estudiante': estudiante,
        'matriculas': matriculas,
        'cursos_disponibles': cursos_disponibles,
        'notificaciones_no_leidas': notificaciones_no_leidas,
        'total_notificaciones_no_leidas': notificaciones_no_leidas.count()
    })

@login_required
@profesor_required
def crear_curso(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        descripcion = request.POST.get('descripcion', '')
        creditos = request.POST.get('creditos', 3)
        cupos = request.POST.get('cupos', 30)
        
        try:
            curso = Curso.objects.create(
                nombre=nombre,
                codigo=codigo,
                descripcion=descripcion,
                creditos=int(creditos),
                cupos_totales=int(cupos),
                cupos_disponibles=int(cupos),
                profesor=request.user.profesor
            )
            messages.success(request, f'Curso {curso.nombre} creado exitosamente.')
            return redirect('dashboard_profesor')
        except Exception as e:
            messages.error(request, f'Error al crear el curso: {str(e)}')
    
    return redirect('dashboard_profesor')

@login_required
@profesor_required
def dashboard_profesor(request):
    profesor = request.user.profesor
    
    # Obtener los cursos del profesor con el conteo de estudiantes matriculados
    cursos = Curso.objects.filter(profesor=profesor).annotate(
        total_estudiantes=Count('matricula', filter=Q(matricula__estado='A'))
    )
    
    # Calcular el total de estudiantes en todos los cursos
    total_estudiantes = sum(
        curso.total_estudiantes 
        for curso in cursos 
        if hasattr(curso, 'total_estudiantes')
    )
    
    # Contar calificaciones pendientes (matrículas sin nota)
    total_calificaciones_pendientes = Matricula.objects.filter(
        curso__in=cursos, 
        estado='A',
        nota__isnull=True
    ).count()
    
    # Obtener notificaciones no leídas
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).order_by('-fecha_creacion')[:10]
    
    return render(request, 'matriculas/dashboard_profesor.html', {
        'profesor': profesor,
        'cursos': cursos,
        'total_estudiantes': total_estudiantes,
        'total_calificaciones_pendientes': total_calificaciones_pendientes,
        'notificaciones_no_leidas': notificaciones_no_leidas,
        'total_notificaciones_no_leidas': notificaciones_no_leidas.count()
    })

@login_required
@estudiante_required
def matricular_curso(request, curso_id):
    """
    Vista para que un estudiante se matricule en un curso.
    """
    if not es_estudiante(request.user):
        messages.error(request, 'Acceso restringido a estudiantes.')
        return redirect('index')
    
    curso = get_object_or_404(Curso, id=curso_id)
    estudiante = request.user.estudiante
    
    # Verificar si el estudiante ya está matriculado en este curso
    matricula_existente = Matricula.objects.filter(
        estudiante=estudiante, 
        curso=curso
    ).exists()
    
    if matricula_existente:
        messages.warning(request, f'Ya estás matriculado en el curso {curso.nombre}.')
        return redirect('dashboard_estudiante')
    
    # Verificar si hay cupos disponibles
    if curso.cupos_disponibles <= 0:
        messages.error(request, f'Lo sentimos, no hay cupos disponibles para el curso {curso.nombre}.')
        return redirect('dashboard_estudiante')
    
    if request.method == 'POST':
        form = MatriculaForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear la matrícula
                    matricula = form.save(commit=False)
                    matricula.estudiante = estudiante
                    matricula.curso = curso
                    matricula.fecha_matricula = timezone.now()
                    matricula.save()
                    
                    # Actualizar cupos disponibles
                    curso.cupos_disponibles -= 1
                    curso.save()
                    
                    messages.success(
                        request, 
                        f'¡Te has matriculado exitosamente en {curso.nombre}!',
                        extra_tags='alert-success'
                    )
                    return redirect('dashboard_estudiante')
                    
            except Exception as e:
                messages.error(
                    request, 
                    f'Ocurrió un error al procesar tu matrícula: {str(e)}',
                    extra_tags='alert-danger'
                )
                logger.error(f'Error al matricular estudiante: {str(e)}')
        else:
            # Si el formulario no es válido, mostrar errores
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error: {error}')
    else:
        form = MatriculaForm()
    
    # Calcular porcentaje de cupos disponibles para la barra de progreso
    # Usamos 100 como valor máximo para el cálculo del porcentaje
    curso.porcentaje_cupos_disponibles = min(100, (curso.cupos_disponibles / 100) * 100) if curso.cupos_disponibles > 0 else 0
    
    return render(request, 'matriculas/matricular_curso.html', {
        'curso': curso,
        'estudiante': estudiante,
        'form': form,
        'matricula_existente': matricula_existente
    })

@login_required
def detalle_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar si el usuario es el profesor del curso
    es_profesor_curso = es_profesor(request.user) and request.user.profesor == curso.profesor
    
    # Obtener todas las matrículas del curso
    matriculas = Matricula.objects.filter(curso=curso).select_related('estudiante__user')
    
    # Separar matrículas aprobadas y pendientes
    matriculas_aprobadas = matriculas.filter(estado='A')
    matriculas_pendientes = matriculas.filter(estado='P')
    
    return render(request, 'matriculas/detalle_curso.html', {
        'curso': curso,
        'matriculas_aprobadas': matriculas_aprobadas,
        'matriculas_pendientes': matriculas_pendientes,
        'es_profesor': es_profesor_curso,
        'es_estudiante': es_estudiante(request.user)
    })

@login_required
@profesor_required
def aprobar_matricula(request, matricula_id, accion):
    """
    Vista para aprobar o rechazar una matrícula.
    accion: 'aprobar' o 'rechazar'
    """
    matricula = get_object_or_404(Matricula, id=matricula_id)
    
    # Verificar que el usuario es el profesor del curso
    if matricula.curso.profesor != request.user.profesor:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('dashboard_profesor')
    
    if accion == 'aprobar':
        matricula.estado = 'A'
        matricula.save()
        messages.success(request, f'Matrícula de {matricula.estudiante.user.get_full_name()} aprobada correctamente.')
    elif accion == 'rechazar':
        matricula.estado = 'R'
        matricula.save()
        messages.warning(request, f'Matrícula de {matricula.estudiante.user.get_full_name()} rechazada.')
    
    return redirect('detalle_curso', curso_id=matricula.curso.id)


@login_required
@estudiante_required
def ver_curso_estudiante(request, curso_id):
    """
    Vista para que un estudiante vea los detalles de un curso en el que está matriculado.
    """
    estudiante = request.user.estudiante
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = Matricula.objects.filter(
        estudiante=estudiante,
        curso=curso
        # Mostrar el curso aunque la matrícula esté pendiente
    ).first()
    
    if not matricula:
        messages.error(request, 'No estás matriculado en este curso o tu matrícula no ha sido aprobada.')
        return redirect('dashboard_estudiante')
    
    # Obtener información del curso
    tareas = curso.tareas.all().order_by('fecha_limite')
    entregas = EntregaTarea.objects.filter(
        estudiante=estudiante,
        tarea__in=tareas
    )
    
    # Crear un diccionario de entregas por tarea para fácil acceso
    entregas_por_tarea = {entrega.tarea_id: entrega for entrega in entregas}
    
    # Preparar datos para la plantilla
    tareas_con_estado = []
    for tarea in tareas:
        entrega = entregas_por_tarea.get(tarea.id)
        tareas_con_estado.append({
            'tarea': tarea,
            'entregada': entrega is not None,
            'calificacion': entrega.calificacion if entrega else None,
            'estado': entrega.estado if entrega else 'P'  # P = Pendiente
        })
    
    # Determinar la condición del estudiante basado en la nota
    condicion = 'Cursando'
    if matricula.nota is not None:
        if matricula.nota >= 13:
            condicion = 'Aprobado'
        else:
            condicion = 'Desaprobado'
    
    # Preparar el contexto con toda la información necesaria
    context = {
        'curso': curso,
        'matricula': matricula,
        'tareas': tareas_con_estado,
        'es_profesor': False,
        'profesor': curso.profesor,
        'horario': curso.horario,
        'aula': curso.aula,
        'creditos': curso.creditos,
        'estado_matricula': matricula.get_estado_display(),
        'condicion_estudiante': condicion,
        'nota': matricula.nota or 'Sin calificar',
    }
    
    return render(request, 'matriculas/ver_curso_estudiante.html', context)

@login_required
@profesor_required
def ver_contenido_curso(request, curso_id):
    """
    Vista para ver el contenido de un curso organizado por semanas.
    """
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Verificar que el usuario es el profesor del curso
    if curso.profesor.user != request.user:
        return HttpResponseForbidden("No tienes permiso para ver el contenido de este curso")
    
    # Obtener todas las tareas del curso agrupadas por semana
    # En una implementación real, podrías tener un modelo Semana o similar
    # Por ahora, usaremos un diccionario simple para el ejemplo
    semanas = {}
    for i in range(1, 19):
        semanas[f'Semana {i}'] = {
            'tareas': [],
            'materiales': []
        }
    
    # Agregar tareas existentes a sus respectivas semanas
    tareas = curso.tareas.all()  # Usando el related_name 'tareas' definido en el modelo
    for tarea in tareas:
        # Si la tarea tiene una semana definida, usarla; de lo contrario, ponerla en la semana 1
        semana = f'Semana {tarea.semana if hasattr(tarea, 'semana') else 1}'
        if semana in semanas:
            semanas[semana]['tareas'].append(tarea)
    
    # Agregar aquí la lógica para cargar otros tipos de contenido (materiales, etc.)
    
    return render(request, 'matriculas/contenido_curso.html', {
        'curso': curso,
        'semanas': semanas.items(),
        'es_profesor': True,  # Para controlar qué botones mostrar en la plantilla
    })

@login_required
@estudiante_required
def ver_contenido_curso_estudiante(request, curso_id):
    """
    Vista para que un estudiante vea el contenido de un curso.
    Similar a la vista del profesor pero sin opciones de edición.
    """
    # Obtener el curso y verificar que el estudiante está matriculado
    curso = get_object_or_404(Curso, id=curso_id)
    estudiante = request.user.estudiante
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = Matricula.objects.filter(estudiante=estudiante, curso=curso).first()
    if not matricula:
        messages.error(request, 'No estás matriculado en este curso.')
        return redirect('dashboard_estudi')
    
    # Verificar si la matrícula está pendiente para mostrar un mensaje informativo
    if matricula.estado != 'A':
        messages.info(request, 'Tu matrícula está pendiente de aprobación. Puedes ver el contenido pero no podrás realizar entregas hasta que sea aprobada.')
    
    # Obtener todas las semanas (1-18) con su contenido
    semanas = {}
    for i in range(1, 19):
        semanas[f'Semana {i}'] = {
            'tareas': [],
            'materiales': []
        }
    
    # Agregar tareas existentes a sus respectivas semanas
    tareas = curso.tareas.all()
    for tarea in tareas:
        semana = f'Semana {tarea.semana if hasattr(tarea, 'semana') else 1}'
        if semana in semanas:
            # Verificar si el estudiante ya entregó esta tarea
            entrega = EntregaTarea.objects.filter(
                tarea=tarea, 
                estudiante=estudiante
            ).first()
            
            # Agregar información de la entrega a la tarea
            tarea.entregada = entrega is not None
            tarea.estado_entrega = entrega.estado if entrega else 'P'
            tarea.calificacion = entrega.calificacion if entrega else None
            
            semanas[semana]['tareas'].append(tarea)
    
    # Agregar aquí la lógica para cargar otros tipos de contenido (materiales, etc.)
    
    return render(request, 'matriculas/contenido_curso_estudiante.html', {
        'curso': curso,
        'semanas': semanas.items(),
        'es_profesor': False,  # Para controlar qué botones mostrar en la plantilla
    })

@login_required
def editar_perfil(request):
    """
    Vista para editar el perfil del usuario autenticado.
    Maneja tanto el perfil de usuario base como los perfiles específicos de estudiante o profesor.
    """
    user = request.user
    context = {}
    
    if request.method == 'POST':
        user_form = EditarPerfilUsuarioForm(request.POST, instance=user)
        
        if hasattr(user, 'estudiante'):
            profile_form = EditarPerfilEstudianteForm(
                request.POST, 
                instance=user.estudiante
            )
            profile = user.estudiante
        elif hasattr(user, 'profesor'):
            profile_form = EditarPerfilProfesorForm(
                request.POST, 
                instance=user.profesor
            )
            profile = user.profesor
        else:
            profile_form = None
            profile = None
        
        # Validar ambos formularios
        if user_form.is_valid():
            user_form.save()
            
            if profile_form and profile and profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('editar_perfil')
            elif not hasattr(user, 'estudiante') and not hasattr(user, 'profesor'):
                # Si es un usuario sin perfil extendido
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('editar_perfil')
    else:
        user_form = EditarPerfilUsuarioForm(instance=user)
        
        if hasattr(user, 'estudiante'):
            profile_form = EditarPerfilEstudianteForm(instance=user.estudiante)
            profile_type = 'estudiante'
        elif hasattr(user, 'profesor'):
            profile_form = EditarPerfilProfesorForm(instance=user.profesor)
            profile_type = 'profesor'
        else:
            profile_form = None
            profile_type = None
    
    context.update({
        'user_form': user_form,
        'profile_form': profile_form,
        'profile_type': profile_type,
    })
    
    # Determinar qué template usar según el tipo de usuario
    if hasattr(user, 'estudiante'):
        template = 'matriculas/editar_perfil_estudiante.html'
    elif hasattr(user, 'profesor'):
        template = 'matriculas/editar_perfil_profesor.html'
    else:
        template = 'matriculas/editar_perfil.html'
    
    return render(request, template, context)


def exportar_calificaciones(request, curso_id):
    """
    Exporta las calificaciones de un curso en diferentes formatos (Excel, CSV).
    """
    # Obtener el curso y verificar que el usuario es el profesor
    curso = get_object_or_404(Curso, id=curso_id)
    
    if not hasattr(request.user, 'profesor') or curso.profesor != request.user.profesor:
        messages.error(request, 'No tienes permiso para exportar las calificaciones de este curso.')
        return redirect('dashboard_profesor')
    
    # Obtener todas las matrículas del curso
    matriculas = Matricula.objects.filter(curso=curso).select_related('estudiante__user')
    
    # Obtener el formato de exportación (por defecto Excel)
    formato = request.GET.get('formato', 'excel')
    
    if formato == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="calificaciones_{curso.codigo}.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Calificaciones')
        
        # Estilos
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        
        # Encabezados
        columns = ['Código', 'Estudiante', 'Nota', 'Estado']
        for col_num, column_title in enumerate(columns):
            ws.write(0, col_num, column_title, font_style)
        
        # Datos
        for row_num, matricula in enumerate(matriculas, 1):
            ws.write(row_num, 0, matricula.estudiante.codigo_estudiante)
            ws.write(row_num, 1, f"{matricula.estudiante.user.get_full_name() or matricula.estudiante.user.username}")
            ws.write(row_num, 2, matricula.nota or '')
            ws.write(row_num, 3, matricula.get_estado_display())
        
        wb.save(response)
        return response
        
    elif formato == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="calificaciones_{curso.codigo}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Código', 'Estudiante', 'Nota', 'Estado'])
        
        for matricula in matriculas:
            writer.writerow([
                matricula.estudiante.codigo_estudiante,
                f"{matricula.estudiante.user.get_full_name() or matricula.estudiante.user.username}",
                matricula.nota or '',
                matricula.get_estado_display()
            ])
        
        return response
    
    # Por defecto, redirigir al detalle del curso
    messages.warning(request, 'Formato de exportación no soportado. Se usó Excel por defecto.')
    return redirect('detalle_curso', curso_id=curso.id)
