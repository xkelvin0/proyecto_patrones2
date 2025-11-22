from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('matriculas', '0004_alter_notificacion_curso_alter_notificacion_tarea'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notificacion',
            name='curso',
        ),
        migrations.RemoveField(
            model_name='notificacion',
            name='tarea',
        ),
        migrations.RemoveField(
            model_name='notificacion',
            name='usuario',
        ),
        migrations.DeleteModel(
            name='Notificacion',
        ),
    ]
