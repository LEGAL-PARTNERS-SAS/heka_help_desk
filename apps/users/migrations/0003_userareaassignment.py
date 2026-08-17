from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('users', '0002_user_optional_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAreaAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(
                    db_column='user_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='area_assignments',
                    to='users.user',
                )),
                ('area', models.ForeignKey(
                    db_column='area_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_assignments',
                    to='core.area',
                )),
            ],
            options={
                'verbose_name': 'Asignación de Área',
                'verbose_name_plural': 'Asignaciones de Área',
                'db_table': 'user_area_assignments',
                'unique_together': {('user', 'area')},
            },
        ),
    ]
