"""
Migration 0002: Make identification, name, lastname optional on the Django model.
NOTE: Since the 'users' table is managed=False, Django does NOT alter the real DB.
You must run the SQL script (migration_sql.sql) on your database manually.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='identification',
            field=models.CharField(
                max_length=20, unique=True, blank=True, null=True,
                db_column='identification'
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='name',
            field=models.CharField(max_length=100, blank=True, default='', db_column='name'),
        ),
        migrations.AlterField(
            model_name='user',
            name='lastname',
            field=models.CharField(max_length=100, blank=True, default='', db_column='lastname'),
        ),
    ]
