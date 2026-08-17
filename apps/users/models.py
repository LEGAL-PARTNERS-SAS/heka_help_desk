"""
apps/users/models.py
Modelo de usuario: autenticación por EMAIL únicamente.
Campos eliminados: identification, username.
"""

from django.db import models, router
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from apps.core.models import Area, Role


class UserStatusChoices(models.TextChoices):
    ACTIVO   = 'activo',   'Activo'
    INACTIVO = 'inactivo', 'Inactivo'


class UserManager(BaseUserManager):
    def createUser(self, email, password=None, **extraFields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user  = self.model(email=email, **extraFields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def createSuperuser(self, email, password=None, **extraFields):
        extraFields.setdefault('is_staff', True)
        extraFields.setdefault('is_superuser', True)

        if 'role' not in extraFields and 'role_id' not in extraFields:
            role, _ = Role.objects.get_or_create(
                roleName='Administrador',
                defaults={'description': 'Super administrador del sistema'},
            )
            extraFields['role'] = role

        if 'area' not in extraFields and 'area_id' not in extraFields:
            area = Area.objects.first()
            if area is None:
                area, _ = Area.objects.get_or_create(areaName='General')
            extraFields['area'] = area

        return self.createUser(email, password, **extraFields)

    # Alias requeridos por Django internamente
    create_user      = createUser
    create_superuser = createSuperuser


class UserAreaAssignment(models.Model):
    """Tabla intermedia para asignación múltiple de áreas a un usuario."""
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='user_id', related_name='area_assignments'
    )
    area = models.ForeignKey(
        Area, on_delete=models.CASCADE,
        db_column='area_id', related_name='user_assignments'
    )

    class Meta:
        managed = False
        db_table = 'user_area_assignments'
        unique_together = (('user', 'area'),)
        verbose_name = 'Asignación de Área'
        verbose_name_plural = 'Asignaciones de Área'

    def __str__(self):
        return f'{self.user} → {self.area}'


class User(AbstractBaseUser, PermissionsMixin):
    userId    = models.AutoField(primary_key=True, db_column='user_id')
    email     = models.EmailField(max_length=150, unique=True, db_column='email')
    name      = models.CharField(max_length=100, blank=True, default='', db_column='name')
    lastname  = models.CharField(max_length=100, blank=True, default='', db_column='lastname')
    role      = models.ForeignKey(
                    Role, on_delete=models.RESTRICT,
                    db_column='role_id', related_name='users'
                )
    area      = models.ForeignKey(
                    Area, on_delete=models.RESTRICT,
                    db_column='area_id', related_name='users'
                )
    status    = models.CharField(
                    max_length=10,
                    choices=UserStatusChoices.choices,
                    default=UserStatusChoices.ACTIVO,
                    db_column='status'
                )
    createdAt = models.DateTimeField(auto_now_add=True, db_column='created_at')
    is_staff  = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []           # solo email + password para createsuperuser

    class Meta:
        managed = False
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['lastname', 'name']

    def __str__(self):
        return self.email

    @property
    def fullName(self):
        name = f'{self.name} {self.lastname}'.strip()
        return name if name else self.email

    # username virtual — Django Admin y algunas partes internas lo esperan
    @property
    def username(self):
        return self.email

    def delete(self, using=None, keep_parents=False):
        using = using or router.db_for_write(self.__class__, instance=self)
        from django.db import connections
        with connections[using].cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id = %s", [self.pk])

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_active and self.is_superuser
