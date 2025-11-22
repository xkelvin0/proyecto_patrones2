from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.db import transaction

# Importar el modelo Notificacion de la aplicación actual
from .models import Notificacion

@login_required
def eliminar_notificacion(request, notificacion_id):
    """
    Vista para eliminar una notificación específica del usuario.
    """
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    
    if request.method == 'POST':
        notificacion.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
            
        messages.success(request, 'Notificación eliminada correctamente')
        return redirect('dashboard_estudiante' if hasattr(request.user, 'estudiante') else 'dashboard_profesor')
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

@login_required
def eliminar_todas_notificaciones(request):
    """
    Vista para eliminar todas las notificaciones del usuario.
    """
    if request.method == 'POST':
        notificaciones = Notificacion.objects.filter(usuario=request.user)
        count = notificaciones.count()
        notificaciones.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': f'Se eliminaron {count} notificaciones',
                'count': 0
            })
            
        messages.success(request, f'Se eliminaron {count} notificaciones')
        return redirect('dashboard_estudiante' if hasattr(request.user, 'estudiante') else 'dashboard_profesor')
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
