from django.apps import AppConfig


class MatriculasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matriculas'
    
    def ready(self):
        # Importar las señales para que estén registradas
        import matriculas.signals
