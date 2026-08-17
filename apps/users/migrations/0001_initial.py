from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password',     models.CharField(max_length=128, verbose_name='password')),
                ('last_login',   models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False)),
                ('userId',       models.AutoField(db_column='user_id', primary_key=True, serialize=False)),
                ('email',        models.EmailField(db_column='email', max_length=150, unique=True)),
                ('name',         models.CharField(blank=True, db_column='name', default='', max_length=100)),
                ('lastname',     models.CharField(blank=True, db_column='lastname', default='', max_length=100)),
                ('status',       models.CharField(
                                     choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')],
                                     db_column='status', default='activo', max_length=10)),
                ('createdAt',    models.DateTimeField(auto_now_add=True, db_column='created_at')),
                ('is_staff',     models.BooleanField(default=False)),
                ('is_active',    models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Usuario',
                'verbose_name_plural': 'Usuarios',
                'db_table': 'users',
                'ordering': ['lastname', 'name'],
                'managed': False,
            },
        ),
    ]
