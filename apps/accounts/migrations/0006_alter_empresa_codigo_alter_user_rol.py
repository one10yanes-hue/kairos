from django.db import migrations, models
import django.db.models.deletion


def fill_null_codigos(apps, schema_editor):
    Empresa = apps.get_model("accounts", "Empresa")
    from apps.core.utils import generar_codigo
    for obj in Empresa.objects.filter(codigo__isnull=True):
        obj.codigo = generar_codigo()
        obj.save()


def fill_null_rol(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Rol = apps.get_model("accounts", "Rol")
    rol_usr = Rol.objects.filter(nombre="Usuario").first()
    if rol_usr:
        for u in User.objects.filter(rol__isnull=True):
            u.rol = rol_usr
            u.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_alter_empresa_nombre_alter_empresa_telefono_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_null_codigos, migrations.RunPython.noop),
        migrations.RunPython(fill_null_rol, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="empresa",
            name="codigo",
            field=models.CharField(blank=True, max_length=6, unique=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="rol",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="usuarios", to="accounts.rol"),
        ),
    ]
