from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Curso(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10, unique=True)
    descripcion = models.TextField(blank=True)
    creditos = models.PositiveIntegerField()
    cupos_disponibles = models.PositiveIntegerField()
    profesor = models.ForeignKey('Profesor', on_delete=models.CASCADE, related_name='cursos')
    horario = models.CharField(max_length=50)
    aula = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class Estudiante(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo_estudiante = models.CharField(max_length=10, unique=True)
    fecha_nacimiento = models.DateField()
    direccion = models.TextField()
    telefono = models.CharField(max_length=15)
    cursos = models.ManyToManyField(Curso, through='Matricula', related_name='estudiantes')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.codigo_estudiante})"

class Profesor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo_profesor = models.CharField(max_length=10, unique=True)
    especialidad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.codigo_profesor})"

class Matricula(models.Model):
    ESTADOS = [
        ('P', 'Pendiente'),
        ('A', 'Aprobada'),
        ('R', 'Rechazada'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=1, choices=ESTADOS, default='P')
    nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                             validators=[MinValueValidator(0), MaxValueValidator(20)])
    
    class Meta:
        unique_together = ('estudiante', 'curso')
    
    def __str__(self):
        return f"{self.estudiante} - {self.curso} - {self.get_estado_display()}"

def ruta_archivo_tarea(instance, filename):
    return f'tareas/{instance.curso.id}/{filename}'

def ruta_entrega_tarea(instance, filename):
    return f'entregas/tarea_{instance.tarea.id}/estudiante_{instance.estudiante.id}/{filename}'

def ruta_archivo_material(instance, filename):
    return f'materiales/curso_{instance.curso.id}/{filename}'

class Material(models.Model):
    """
    Modelo para representar los materiales de un curso.
    Puede ser un archivo o un enlace a un recurso externo.
    """
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='materiales')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    semana = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(16)])
    archivo = models.FileField(upload_to=ruta_archivo_material, null=True, blank=True)
    enlace = models.URLField(blank=True, null=True)
    es_anuncio = models.BooleanField(default=False, help_text='Indica si este material es un anuncio')
    
    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre}"
    
    def tipo_material(self):
        if self.archivo:
            return 'archivo'
        elif self.enlace:
            return 'enlace'
        return 'sin_archivo'

class Tarea(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='tareas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateTimeField()
    archivo = models.FileField(upload_to=ruta_archivo_tarea, null=True, blank=True)
    puntos = models.PositiveIntegerField(default=100)
    
    class Meta:
        ordering = ['-fecha_limite']
    
    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre}"


class EntregaTarea(models.Model):
    ESTADOS = [
        ('P', 'Pendiente de revisión'),
        ('C', 'Calificado'),
        ('A', 'Aprobado'),
        ('R', 'Rechazado'),
    ]
    
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='entregas_tareas')
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    archivo = models.FileField(upload_to=ruta_entrega_tarea)
    comentario_estudiante = models.TextField(blank=True)
    comentario_profesor = models.TextField(blank=True)
    calificacion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=1, choices=ESTADOS, default='P')
    
    class Meta:
        unique_together = ('tarea', 'estudiante')
        ordering = ['-fecha_entrega']
    
    def __str__(self):
        return f"{self.estudiante} - {self.tarea}"
    
    def esta_retrasada(self):
        return self.fecha_entrega > self.tarea.fecha_limite


class Notificacion(models.Model):
    """
    Modelo para representar las notificaciones del sistema.
    """
    TIPOS_NOTIFICACION = [
        ('curso', 'Curso'),
        ('tarea', 'Tarea'),
        ('sistema', 'Sistema'),
        ('mensaje', 'Mensaje')
    ]
    
    usuario = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='notificaciones'
    )
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(
        max_length=20, 
        choices=TIPOS_NOTIFICACION, 
        default='sistema'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    url = models.URLField(blank=True, null=True)
    curso = models.ForeignKey(
        Curso, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notificaciones'
    )
    tarea = models.ForeignKey(
        Tarea, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notificaciones'
    )

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"
    
    def marcar_como_leida(self):
        """Marca la notificación como leída."""
        if not self.leida:
            self.leida = True
            self.save(update_fields=['leida'])
        return self
