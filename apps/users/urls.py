from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/',      views.loginView,      name='login'),
    path('mfa/',        views.mfaVerifyView,  name='mfa_verify'),
    path('logout/',     views.logoutView,     name='logout'),
    path('perfil/',     views.profileView,    name='profile'),
    path('registro/',   views.registerView,   name='register'),
    path('',            views.userListView,   name='list'),
]
