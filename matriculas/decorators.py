from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from functools import wraps

def profesor_required(view_func):
    """
    Decorador para vistas que verifica que el usuario sea un profesor.
    Si no lo es, redirige a la página de inicio.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'profesor'):
            messages.error(request, 'Acceso denegado. Debes ser profesor para acceder a esta página.')
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def estudiante_required(view_func):
    """
    Decorador para vistas que verifica que el usuario sea un estudiante.
    Si no lo es, redirige a la página de inicio.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'estudiante'):
            messages.error(request, 'Acceso denegado. Debes ser estudiante para acceder a esta página.')
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def profesor_o_estudiante_required(view_func):
    """
    Decorador para vistas que verifica que el usuario sea un profesor o un estudiante.
    Si no lo es, redirige a la página de inicio.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (hasattr(request.user, 'profesor') or hasattr(request.user, 'estudiante')):
            messages.error(request, 'Acceso denegado. Debes iniciar sesión como profesor o estudiante.')
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def profesor_propietario_required(model_class, id_param='pk', id_kwarg='pk'):
    """
    Decorador para verificar que el profesor es el propietario del recurso.
    Útil para asegurar que un profesor solo pueda modificar sus propios cursos/tareas.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'profesor'):
                raise PermissionDenied("Acceso denegado. Debes ser profesor.")
                
            # Obtener el ID del objeto de los argumentos de la URL
            obj_id = kwargs.get(id_kwarg) or request.GET.get(id_param) or request.POST.get(id_param)
            
            if not obj_id:
                raise ValueError("No se pudo encontrar el parámetro {} en la solicitud.".format(id_param))
                
            # Obtener el objeto y verificar que pertenece al profesor
            try:
                obj = model_class.objects.get(id=obj_id)
            except model_class.DoesNotExist:
                raise PermissionDenied("El recurso solicitado no existe.")
                
            # Verificar que el profesor es el propietario
            if hasattr(obj, 'profesor') and obj.profesor != request.user.profesor:
                raise PermissionDenied("No tienes permiso para acceder a este recurso.")
                
            # Si el objeto es una tarea, verificar que pertenece a un curso del profesor
            if hasattr(obj, 'curso') and obj.curso.profesor != request.user.profesor:
                raise PermissionDenied("No tienes permiso para acceder a esta tarea.")
                
            # Pasar el objeto a la vista
            kwargs['object'] = obj
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
