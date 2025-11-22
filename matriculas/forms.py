from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from .models import Estudiante, Profesor, Matricula, Curso, Tarea, EntregaTarea, Material

class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        help_text='Requerido. Ingrese un correo válido.',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@dominio.com'})
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        help_text='Requerido. Ingrese su nombre.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True, 
        help_text='Requerido. Ingrese su apellido.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrónico ya está registrado')
        return email

class RegistroEstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ['codigo_estudiante', 'fecha_nacimiento', 'direccion', 'telefono']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'max': timezone.now().date().isoformat()}),
            'direccion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ingrese su dirección completa'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: +51 987654321'}),
            'codigo_estudiante': forms.TextInput(attrs={'placeholder': 'Ej: E20230001'}),
        }
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not re.match(r'^\+?\d{9,15}$', telefono):
            raise ValidationError('Formato de teléfono inválido. Use el formato: +51987654321')
        return telefono
    
    def clean_codigo_estudiante(self):
        codigo = self.cleaned_data.get('codigo_estudiante')
        if not re.match(r'^E\d{8}$', codigo):
            raise ValidationError('El código de estudiante debe tener el formato E seguido de 8 dígitos')
        if Estudiante.objects.filter(codigo_estudiante=codigo).exists():
            raise ValidationError('Este código de estudiante ya está registrado')
        return codigo

class RegistroProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        fields = ['codigo_profesor', 'especialidad', 'telefono']
        widgets = {
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: +51 987654321'}),
            'codigo_profesor': forms.TextInput(attrs={'placeholder': 'Ej: P2023001'}),
            'especialidad': forms.TextInput(attrs={'placeholder': 'Ej: Ingeniería de Software'}),
        }
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not re.match(r'^\+?\d{9,15}$', telefono):
            raise ValidationError('Formato de teléfono inválido. Use el formato: +51987654321')
        return telefono
    
    def clean_codigo_profesor(self):
        codigo = self.cleaned_data.get('codigo_profesor')
        if not re.match(r'^P\d{6}$', codigo):
            raise ValidationError('El código de profesor debe tener el formato P seguido de 6 dígitos')
        if Profesor.objects.filter(codigo_profesor=codigo).exists():
            raise ValidationError('Este código de profesor ya está registrado')
        return codigo

class MatriculaForm(forms.ModelForm):
    class Meta:
        model = Matricula
        fields = []  # No necesitamos campos adicionales, ya que el estado se asigna automáticamente
    
    def save(self, commit=True):
        # Sobrescribimos el método save para asegurarnos de que el estado sea 'P' (Pendiente)
        matricula = super().save(commit=False)
        matricula.estado = 'P'  # Estado por defecto: Pendiente
        if commit:
            matricula.save()
        return matricula

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre', 'codigo', 'descripcion', 'creditos', 'cupos_disponibles', 'profesor', 'horario', 'aula']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Programación Avanzada'}),
            'codigo': forms.TextInput(attrs={'placeholder': 'Ej: PROG301'}),
            'descripcion': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Ingrese una descripción detallada del curso'
            }),
            'horario': forms.TextInput(attrs={'placeholder': 'Ej: Lunes y Miércoles 14:00-16:00'}),
            'aula': forms.TextInput(attrs={'placeholder': 'Ej: A-201'}),
            'creditos': forms.NumberInput(attrs={'min': 1, 'max': 6}),
            'cupos_disponibles': forms.NumberInput(attrs={'min': 1, 'max': 50}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo los usuarios que son profesores
        self.fields['profesor'].queryset = Profesor.objects.select_related('user')
        self.fields['profesor'].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.codigo_profesor})"
    
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if not re.match(r'^[A-Z]{3,4}\d{3}$', codigo):
            raise ValidationError('El código del curso debe tener 3-4 letras seguidas de 3 dígitos (ej: PROG301)')
        return codigo
    
    def clean_creditos(self):
        creditos = self.cleaned_data.get('creditos')
        if not 1 <= creditos <= 6:
            raise ValidationError('Los créditos deben estar entre 1 y 6')
        return creditos
    
    def clean_cupos_disponibles(self):
        cupos = self.cleaned_data.get('cupos_disponibles')
        if cupos < 1 or cupos > 50:
            raise ValidationError('Los cupos disponibles deben estar entre 1 y 50')
        return cupos

class TareaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['puntos'].initial = 20
        self.fields['fecha_limite'].input_formats = ['%Y-%m-%dT%H:%M']
        
    class Meta:
        model = Tarea
        fields = ['titulo', 'descripcion', 'fecha_limite', 'archivo', 'puntos']
        widgets = {
            'fecha_limite': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'puntos': forms.NumberInput(attrs={'min': 1, 'max': 20}),
        }

class EntregaTareaForm(forms.ModelForm):
    class Meta:
        model = EntregaTarea
        fields = ['archivo', 'comentario_estudiante']
        widgets = {
            'comentario_estudiante': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Agrega algún comentario sobre tu entrega (opcional)'}),
        }

class CalificarTareaForm(forms.ModelForm):
    class Meta:
        model = EntregaTarea
        fields = ['calificacion', 'comentario_profesor', 'estado']
        widgets = {
            'comentario_profesor': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comentarios sobre la entrega...'}),
            'calificacion': forms.NumberInput(attrs={'min': 0, 'max': 20, 'step': '0.01'}),
        }
    
class EditarTareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo', 'descripcion', 'fecha_limite', 'puntos', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'fecha_limite': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'puntos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'step': 1}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que el campo de fecha tenga el formato correcto
        self.fields['fecha_limite'].input_formats = ['%Y-%m-%dT%H:%M']

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['titulo', 'descripcion', 'semana', 'archivo', 'enlace']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'semana': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 16}),
            'archivo': forms.FileInput(attrs={'class': 'form-control'}),
            'enlace': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://ejemplo.com'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        archivo = cleaned_data.get('archivo')
        enlace = cleaned_data.get('enlace')
        
        if not archivo and not enlace:
            raise forms.ValidationError('Debes proporcionar un archivo o un enlace.')
        
        return cleaned_data


class EditarPerfilUsuarioForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget = forms.HiddenInput()

class EditarPerfilEstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ('fecha_nacimiento', 'direccion', 'telefono')
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

class EditarPerfilProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        fields = ('especialidad', 'telefono')
        widgets = {
            'especialidad': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
