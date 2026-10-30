from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('',                        views.adminDashboardView,  name='dashboard'),

    # Áreas
    path('areas/',                  views.areaListView,        name='areas'),
    path('areas/nueva/',            views.areaCreateView,      name='area_create'),
    path('areas/<int:pk>/editar/',  views.areaEditView,        name='area_edit'),
    path('areas/<int:pk>/eliminar/', views.areaDeleteView,     name='area_delete'),

    # Roles
    path('roles/',                  views.roleListView,        name='roles'),
    path('roles/nuevo/',            views.roleCreateView,      name='role_create'),
    path('roles/<int:pk>/editar/',  views.roleEditView,        name='role_edit'),
    path('roles/<int:pk>/eliminar/', views.roleDeleteView,     name='role_delete'),

    # Categorías
    path('categorias/',             views.categoryListView,    name='categories'),
    path('categorias/nueva/',       views.categoryCreateView,  name='category_create'),
    path('categorias/<int:pk>/editar/', views.categoryEditView, name='category_edit'),
    path('categorias/<int:pk>/eliminar/', views.categoryDeleteView, name='category_delete'),

    # Usuarios
    path('usuarios/',               views.userAdminListView,   name='usuarios'),
    path('usuarios/nuevo/',         views.userAdminCreateView, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.userAdminEditView, name='user_edit'),
    path('usuarios/<int:pk>/eliminar/', views.userAdminDeleteView, name='user_delete'),

    # Reportería
    path('reportes/',              views.reportesView,         name='reportes'),
]
