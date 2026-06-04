from django.db import migrations, models


def fill_null_codigos(apps, schema_editor):
    from apps.core.utils import generar_codigo
    for model_name in ("TipoActividad", "Actividad"):
        Model = apps.get_model("actividades", model_name)
        for obj in Model.objects.filter(codigo__isnull=True):
            obj.codigo = generar_codigo()
            obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0005_alter_actividad_nombre_alter_tipoactividad_nombre"),
    ]

    operations = [
        migrations.RunPython(fill_null_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="actividad",
            name="codigo",
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
        migrations.AlterField(
            model_name="tipoactividad",
            name="codigo",
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
    ]
