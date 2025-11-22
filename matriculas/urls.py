from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from . import views

# Import the view class at the top of the file
from .views import CustomLoginView

# Importar vistas de tareas
from . import tareas_views

# Importar vistas de materiales
from . import materiales_views

# Importar vistas de anuncios
from . import anuncios_views

# Importar vistas de notificaciones
from . import notificaciones_views

# URLs de notificaciones
notificaciones_patterns = [
    path('notificacion/eliminar/<int:notificacion_id>/', notificaciones_views.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/eliminar-todas/', notificaciones_views.eliminar_todas_notificaciones, name='eliminar_todas_notificaciones'),
]

# URLs de autenticación
auth_patterns = [
    # URLs de autenticación personalizadas
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/registro/estudiante/', views.registro_estudiante, name='registro_estudiante'),
    path('accounts/registro/profesor/', views.registro_profesor, name='registro_profesor'),
    
    # Redireccionar las URLs predeterminadas a las personalizadas
    path('login/', CustomLoginView.as_view(), name='login_redirect'),
    path('logout/', views.logout_view, name='logout_redirect'),
]

# URLs de estudiantes
estudiante_patterns = [
    path('', views.dashboard_estudiante, name='dashboard_estudiante'),
    path('matricular/<int:curso_id>/', views.matricular_curso, name='matricular_curso'),
    path('ver-curso/<int:curso_id>/', views.ver_curso_estudiante, name='ver_curso_estudiante'),
    # URLs de contenido del curso y tareas para estudiantes
    path('curso/<int:curso_id>/contenido/', views.ver_contenido_curso_estudiante, name='ver_contenido_estudiante'),
    path('curso/<int:curso_id>/tareas/', tareas_views.listar_tareas_estudiante, name='listar_tareas_estudiante'),
    path('tarea/<int:tarea_id>/', tareas_views.ver_tarea, name='ver_tarea'),
    path('tarea/<int:tarea_id>/entregar/', tareas_views.ver_tarea, name='entregar_tarea'),
    path('tarea/archivo/<int:tarea_id>/', tareas_views.descargar_archivo_tarea, name='descargar_archivo_tarea'),
    path('entrega/archivo/<int:entrega_id>/', tareas_views.descargar_entrega, name='descargar_entrega'),
]


# URLs de profesores
profesor_patterns = [
    path('', views.dashboard_profesor, name='dashboard_profesor'),
    path('curso/crear/', views.crear_curso, name='crear_curso'),
    path('curso/<int:curso_id>/', views.detalle_curso, name='detalle_curso'),
    path('matricula/<int:matricula_id>/<str:accion>/', views.aprobar_matricula, name='aprobar_matricula'),
    path('curso/<int:curso_id>/exportar/', views.exportar_calificaciones, name='exportar_calificaciones'),
    
    # URLs de contenido del curso, tareas y materiales
    path('curso/<int:curso_id>/contenido/', views.ver_contenido_curso, name='ver_contenido_curso'),
    path('curso/<int:curso_id>/tarea/crear/', tareas_views.crear_tarea, name='crear_tarea'),
    path('curso/<int:curso_id>/anuncio/crear/', anuncios_views.crear_anuncio, name='crear_anuncio'),
    path('curso/<int:curso_id>/material/subir/', materiales_views.subir_material, name='subir_material'),
    path('tarea/<int:tarea_id>/', tareas_views.ver_tarea, name='ver_tarea_profesor'),
    path('tarea/<int:tarea_id>/editar/', tareas_views.editar_tarea, name='editar_tarea'),
    path('tarea/<int:tarea_id>/eliminar/', tareas_views.eliminar_tarea, name='eliminar_tarea'),
    path('tarea/<int:tarea_id>/exportar/', tareas_views.exportar_tarea, name='exportar_tarea'),
    path('entrega/<int:entrega_id>/', tareas_views.ver_entrega, name='ver_entrega'),
    path('entrega/<int:entrega_id>/calificar/', tareas_views.calificar_entrega, name='calificar_entrega'),
    path('entrega/archivo/<int:entrega_id>/', tareas_views.descargar_entrega, name='descargar_entrega_profesor'),
    path('tarea/archivo/<int:tarea_id>/', tareas_views.descargar_archivo_tarea, name='descargar_archivo_tarea_profesor'),
]

# URLs principales
urlpatterns = [
    # Incluir URLs de notificaciones
    path('notificaciones/', include((notificaciones_patterns, 'notificaciones'))),
    path('', views.index, name='index'),
    path('auth/', include(auth_patterns)),
    path('estudiante/', include(estudiante_patterns)),
    path('profesor/', include(profesor_patterns)),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('admin/', admin.site.urls),  # Si usas el admin de Django
]

# Servir archivos de medios en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)