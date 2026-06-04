from django.db import migrations, models


def fill_null_codigos(apps, schema_editor):
    from apps.core.utils import generar_codigo
    for model_name in ("Area", "SubArea"):
        Model = apps.get_model("estructura", model_name)
        for obj in Model.objects.filter(codigo__isnull=True):
            obj.codigo = generar_codigo()
            obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("estructura", "0003_alter_area_nombre_alter_subarea_nombre"),
    ]

    operations = [
        migrations.RunPython(fill_null_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="area",
            name="codigo",
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
        migrations.AlterField(
            model_name="subarea",
            name="codigo",
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
    ]
