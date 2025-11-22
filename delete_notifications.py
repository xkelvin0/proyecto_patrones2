import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_matriculas_django.settings')
django.setup()

# Importa los modelos después de configurar Django
from django.db import connection
def delete_notifications():
    with connection.cursor() as cursor:
        # Verifica si la tabla existe antes de intentar borrarla
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='matriculas_notificacion';
        """)
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("Eliminando notificaciones...")
            cursor.execute("DROP TABLE matriculas_notificacion;")
            print("¡Notificaciones eliminadas exitosamente!")
        else:
            print("No se encontró la tabla de notificaciones.")

if __name__ == "__main__":
    delete_notifications()
