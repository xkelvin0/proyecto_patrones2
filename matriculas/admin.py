from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
import csv
from datetime import datetime

from .models import Estudiante, Profesor, Curso, Matricula

# Registrar el modelo User personalizado
User = get_user_model()

# Desregistrar el modelo User si ya está registrado
if admin.site.is_registered(User):
    admin.site.unregister(User)

# Personalizar la cabecera del admin
admin.site.site_header = 'Administración de EduMatriculas'
admin.site.site_title = 'EduMatriculas Admin'
admin.site.index_title = 'Panel de Control'

# Clases personalizadas para el admin
class EstudianteInline(admin.StackedInline):
    model = Estudiante
    can_delete = False
    verbose_name_plural = 'Información de Estudiante'
    fk_name = 'user'
    readonly_fields = ('matriculas_count',)  # Solo mantener campos que existen
    fieldsets = (
        (None, {
            'fields': ('codigo_estudiante', 'user')
        }),
        ('Información Personal', {
            'fields': ('fecha_nacimiento', 'telefono', 'direccion')
        }),
        ('Información Adicional', {
            'fields': ('matriculas_count', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def matriculas_count(self, instance):
        if instance.pk:
            count = instance.matriculas.count()
            url = (
                reverse('admin:matriculas_matricula_changelist') + 
                f'?estudiante__id__exact={instance.id}'
            )
            return format_html('<a href="{}">{} cursos</a>', url, count)
        return 'N/A'
    matriculas_count.short_description = 'Cursos Matriculados'

class ProfesorInline(admin.StackedInline):
    model = Profesor
    can_delete = False
    verbose_name_plural = 'Información de Profesor'
    fk_name = 'user'
    readonly_fields = ('cursos_count',)  # Solo mantener campos que existen
    fieldsets = (
        (None, {
            'fields': ('codigo_profesor', 'user')
        }),
        ('Información Profesional', {
            'fields': ('especialidad', 'telefono')
        }),
        ('Información Adicional', {
            'fields': ('cursos_count', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def cursos_count(self, instance):
        if instance.pk:
            count = instance.cursos.count()
            url = (
                reverse('admin:matriculas_curso_changelist') + 
                f'?profesor__id__exact={instance.id}'
            )
            return format_html('<a href="{}">{} cursos</a>', url, count)
        return 'N/A'
    cursos_count.short_description = 'Cursos Impartidos'

# Personalizar el UserAdmin para incluir los perfiles
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (EstudianteInline, ProfesorInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_staff', 'date_joined')
    list_display_links = ('username', 'email')
    list_select_related = ('estudiante', 'profesor')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    date_hierarchy = 'date_joined'
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permisos', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas importantes', {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    def user_type(self, obj):
        if hasattr(obj, 'estudiante'):
            return format_html(
                '<span class="badge bg-primary">Estudiante</span> {0}',
                obj.estudiante.codigo_estudiante
            )
        elif hasattr(obj, 'profesor'):
            return format_html(
                '<span class="badge bg-success">Profesor</span> {0}',
                obj.profesor.codigo_profesor
            )
        return format_html('<span class="badge bg-secondary">Administrador</span>')
    user_type.short_description = 'Tipo de Usuario'
    user_type.admin_order_field = 'is_staff'  # Para ordenar por tipo

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

# Acción personalizada para exportar a CSV
def export_to_csv(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}-{datetime.now().strftime("%Y%m%d")}.csv'
    
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
    
    return response
export_to_csv.short_description = 'Exportar seleccionados a CSV'

# Registrar los modelos
@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'profesor_display', 'cupos_disponibles', 'estudiantes_count', 'horario', 'aula')
    list_filter = ('profesor', 'aula')
    search_fields = ('nombre', 'codigo', 'profesor__user__first_name', 'profesor__user__last_name')
    actions = [export_to_csv, 'marcar_activos', 'marcar_inactivos']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Detalles', {
            'fields': ('profesor', 'creditos', 'cupos_disponibles', 'horario', 'aula')
        }),
    )
    
    def profesor_display(self, obj):
        return f"{obj.profesor.user.get_full_name()}" if obj.profesor else "-"
    profesor_display.short_description = 'Profesor'
    profesor_display.admin_order_field = 'profesor__user__last_name'
    
    def estudiantes_count(self, obj):
        # Usar el related_name predeterminado 'matricula_set' ya que no se especificó uno en el modelo
        return obj.matricula_set.count()
    estudiantes_count.short_description = 'Estudiantes'
    
    @admin.action(description='Marcar como inactivos')
    def marcar_inactivos(self, request, queryset):
        # Aquí podrías implementar lógica adicional si es necesario
        count = queryset.count()
        self.message_user(request, f"{count} cursos marcados como inactivos.")
    
    @admin.action(description='Marcar como activos')
    def marcar_activos(self, request, queryset):
        # Aquí podrías implementar lógica adicional si es necesario
        count = queryset.count()
        self.message_user(request, f"{count} cursos marcados como activos.")

@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('id', 'estudiante_display', 'curso_display', 'fecha_matricula', 'estado', 'nota', 'aprobado')
    list_filter = ('estado', 'curso', 'fecha_matricula')
    search_fields = (
        'estudiante__user__first_name', 
        'estudiante__user__last_name', 
        'curso__nombre',
        'curso__codigo'
    )
    date_hierarchy = 'fecha_matricula'
    list_editable = ('estado', 'nota')
    actions = [export_to_csv, 'marcar_aprobadas', 'marcar_pendientes', 'marcar_rechazadas']
    readonly_fields = ('fecha_matricula',)
    
    fieldsets = (
        (None, {
            'fields': ('estudiante', 'curso')
        }),
        ('Calificación', {
            'fields': ('nota', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_matricula',),
            'classes': ('collapse',)
        }),
    )
    
    def estudiante_display(self, obj):
        return obj.estudiante.user.get_full_name()
    estudiante_display.short_description = 'Estudiante'
    estudiante_display.admin_order_field = 'estudiante__user__last_name'
    
    def curso_display(self, obj):
        return f"{obj.curso.codigo} - {obj.curso.nombre}"
    curso_display.short_description = 'Curso'
    curso_display.admin_order_field = 'curso__nombre'
    
    def aprobado(self, obj):
        return obj.nota >= 3.0 if obj.nota is not None else False
    aprobado.boolean = True
    aprobado.short_description = 'Aprobado'
    
    @admin.action(description='Marcar como aprobadas (A)')
    def marcar_aprobadas(self, request, queryset):
        updated = queryset.update(estado='A')
        self.message_user(request, f"{updated} matrículas marcadas como aprobadas.")
    
    @admin.action(description='Marcar como pendientes (P)')
    def marcar_pendientes(self, request, queryset):
        updated = queryset.update(estado='P')
        self.message_user(request, f"{updated} matrículas marcadas como pendientes.")
    
    @admin.action(description='Marcar como rechazadas (R)')
    def marcar_rechazadas(self, request, queryset):
        updated = queryset.update(estado='R')
        self.message_user(request, f"{updated} matrículas marcadas como rechazadas.")

# Personalizar el GroupAdmin
class CustomGroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

# Re-registrar modelos
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)

# Re-registrar UserAdmin con la personalización
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Personalizar el texto del pie de página
def get_footer():
    return 'Sistema de Gestión Académica - EduMatriculas © {}'.format(datetime.now().year)

admin.site.site_footer = get_footer()

# Mejorar la visualización de listas largas
admin.site.enable_nav_sidebar = True

# Configuración de la paginación
admin.site.list_per_page = 25
