from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display  = ('email', 'name', 'lastname', 'role', 'area', 'status', 'is_staff')
    list_filter   = ('role', 'area', 'status', 'is_staff', 'is_superuser')
    search_fields = ('email', 'name', 'lastname')
    ordering      = ('lastname', 'name')
    fieldsets = [
        (None,          {'fields': ('email', 'password')}),
        ('Información', {'fields': ('name', 'lastname', 'role', 'area', 'status')}),
        ('Permisos',    {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    ]
