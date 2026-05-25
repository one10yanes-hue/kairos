from django.db import migrations
from apps.core.utils import generar_codigo


def populate_codigos(apps, schema_editor):
    models_data = [
        ("accounts", "Empresa"),
        ("estructura", "Area"),
        ("estructura", "SubArea"),
        ("actividades", "TipoActividad"),
        ("actividades", "Actividad"),
    ]
    for app, model_name in models_data:
        Model = apps.get_model(app, model_name)
        for obj in Model.objects.filter(codigo__isnull=True):
            obj.codigo = generar_codigo()
            obj.save(update_fields=["codigo"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_empresa_codigo"),
        ("estructura", "0002_area_codigo_subarea_codigo"),
        ("actividades", "0004_actividad_codigo_tipoactividad_codigo"),
    ]
    operations = [
        migrations.RunPython(populate_codigos),
    ]
