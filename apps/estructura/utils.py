"""
Utilidades compartidas para el modulo de estructura.
"""

from apps.estructura.models import SubArea


def get_admin_subareas(user):
    """Devuelve las SubAreas accesibles para el usuario segun su rol.
    Master ve todas. Admin ve solo las asignadas via UserSubArea.
    Soporta roles_adicionales y rol original en BD."""
    if not user.is_authenticated:
        return SubArea.objects.none()
    # Master: todas las activas
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    # Verificar roles_adicionales (sin depender del middleware de switch)
    from apps.accounts.models import User
    db_rol = User.objects.filter(pk=user.pk).values_list("rol__nombre", flat=True).first()
    if db_rol == "Master":
        return SubArea.objects.filter(activo=True)
    if user.roles_adicionales.filter(nombre="Master").exists():
        return SubArea.objects.filter(activo=True)
    # Admin o Usuario: solo las subareas asignadas via UserSubArea
    return SubArea.objects.filter(usuarios__user=user, activo=True)
